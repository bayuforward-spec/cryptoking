"""Self-learning via walk-forward re-tuning — the safe way to "get better".

The danger with self-learning a trading bot is overfitting: tune hard enough on
past data and you get a config that looks brilliant in hindsight and bleeds live.
The guard here is strict out-of-sample validation:

  1. Split recent candles into TRAIN (older) and HOLDOUT (newer).
  2. Grid-search parameters on TRAIN only.
  3. Take the best TRAIN config and measure it on HOLDOUT (data it never saw).
  4. Measure the CURRENT config on the same HOLDOUT.
  5. Promote the new config ONLY if it beats current on the holdout, has a
     positive expected value, and traded enough to be meaningful.

A promotion is written as a *proposal*; applying it is a separate, optional
step (auto-apply, or human approval from the dashboard). The bot never silently
rewrites its own live rules.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field, replace
from pathlib import Path
from typing import Sequence

from .backtest import Backtester
from .config import Config, ExecutionConfig, FeesConfig, RiskConfig, save_config
from .exchange.cryptocom import Candle
from .optimize import optimize
from .strategy import build_strategy


@dataclass
class Metrics:
    expectancy: float
    win_rate: float
    profit_factor: float
    closed_trades: int
    return_pct: float


@dataclass
class Proposal:
    created_at: str
    promote: bool
    reason: str
    strategy_params: dict          # proposed strategy param overrides
    risk_overrides: dict           # proposed risk param overrides
    current_holdout: Metrics
    proposed_holdout: Metrics
    min_trades: int
    applied: bool = False
    ai_note: str = ""

    def as_dict(self) -> dict:
        return asdict(self)


def _evaluate(
    candles: Sequence[Candle],
    strategy_name: str,
    params: dict,
    risk: RiskConfig,
    fees: FeesConfig,
    execution: ExecutionConfig,
    trend_ratio: int,
) -> Metrics:
    strat = build_strategy(strategy_name, params)
    bt = Backtester(strat, risk, fees, trend_ratio=trend_ratio, execution=execution)
    res = bt.run(candles)
    s = res.stats
    return Metrics(
        expectancy=s.expectancy,
        win_rate=s.win_rate,
        profit_factor=(0.0 if s.profit_factor == float("inf") else s.profit_factor),
        closed_trades=s.closed_trades,
        return_pct=res.return_pct,
    )


def walk_forward_retune(
    candles: Sequence[Candle],
    config: Config,
    strategy_grid: list[dict],
    risk_grid: list[dict],
    now_iso: str,
    train_frac: float = 0.6,
    trend_ratio: int = 16,
    min_trades: int = 15,
    improvement: float = 0.0,
) -> Proposal:
    """Run the train→holdout retune and return a Proposal."""
    n = len(candles)
    split = int(n * train_frac)
    train, holdout = candles[:split], candles[split:]

    base_params = config.strategy.params

    # Current config measured on the holdout (the bar to beat).
    current = _evaluate(
        holdout, config.strategy.name, base_params, config.risk,
        config.fees, config.execution, trend_ratio,
    )

    # Optimize on TRAIN only.
    train_results = optimize(
        train,
        config.strategy.name,
        base_params,
        config.risk,
        config.fees,
        strategy_grid=strategy_grid,
        risk_grid=risk_grid,
        trend_ratio=trend_ratio,
        execution=config.execution,
        min_trades=min_trades,
    )
    best = next(
        (r for r in train_results if r.closed_trades >= min_trades and r.expectancy > 0),
        None,
    )

    if best is None:
        return Proposal(
            created_at=now_iso, promote=False,
            reason="no train config reached a positive edge with enough trades",
            strategy_params={}, risk_overrides={},
            current_holdout=current, proposed_holdout=current, min_trades=min_trades,
        )

    # Evaluate the TRAIN winner on the HOLDOUT (true out-of-sample test).
    proposed_params = {**base_params, **best.params}
    proposed_risk = replace(config.risk, **best.risk)
    proposed = _evaluate(
        holdout, config.strategy.name, proposed_params, proposed_risk,
        config.fees, config.execution, trend_ratio,
    )

    promote = (
        proposed.closed_trades >= min_trades
        and proposed.expectancy > 0
        and proposed.expectancy > current.expectancy + improvement
    )
    if promote:
        reason = (
            f"holdout EV {proposed.expectancy:.4f} > current {current.expectancy:.4f} "
            f"over {proposed.closed_trades} out-of-sample trades"
        )
    else:
        reason = (
            f"rejected: holdout EV {proposed.expectancy:.4f} did not beat current "
            f"{current.expectancy:.4f} with a meaningful sample"
        )

    return Proposal(
        created_at=now_iso, promote=promote, reason=reason,
        strategy_params=best.params, risk_overrides=best.risk,
        current_holdout=current, proposed_holdout=proposed, min_trades=min_trades,
    )


def apply_proposal(proposal: Proposal, config: Config, config_path: str) -> None:
    """Apply a promoted proposal onto the live config and persist it."""
    for k, v in proposal.strategy_params.items():
        if k in config.strategy.params:
            config.strategy.params[k] = v
    for k, v in proposal.risk_overrides.items():
        if hasattr(config.risk, k):
            setattr(config.risk, k, v)
    save_config(config, config_path)
    proposal.applied = True


PROPOSAL_PATH = "logs/proposal.json"


def write_proposal(proposal: Proposal, path: str = PROPOSAL_PATH) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(proposal.as_dict(), indent=2), encoding="utf-8")


def read_proposal(path: str = PROPOSAL_PATH) -> dict | None:
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))
