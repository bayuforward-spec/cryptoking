"""Parameter tuner — grid-search strategy/risk params over historical candles
and rank by expected value (the guide's "find a positive edge").

Runs the Backtester for every combination and returns results sorted best-first,
filtering out combos with too few trades to be meaningful.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass, replace
from typing import Sequence

from .backtest import Backtester
from .config import ExecutionConfig, FeesConfig, RiskConfig
from .exchange.cryptocom import Candle
from .strategy import build_strategy


@dataclass
class TuneResult:
    params: dict          # strategy params used
    risk: dict            # risk params overridden
    expectancy: float
    win_rate: float
    profit_factor: float
    closed_trades: int
    return_pct: float


def grid(**axes) -> list[dict]:
    """Cartesian product of named axes -> list of param dicts."""
    keys = list(axes.keys())
    combos = itertools.product(*(axes[k] for k in keys))
    return [dict(zip(keys, vals)) for vals in combos]


def optimize(
    candles: Sequence[Candle],
    strategy_name: str,
    base_strategy_params: dict,
    base_risk: RiskConfig,
    fees: FeesConfig,
    strategy_grid: list[dict],
    risk_grid: list[dict] | None = None,
    trend_ratio: int = 16,
    execution: ExecutionConfig | None = None,
    min_trades: int = 20,
    instrument: str = "BTC_USDT",
) -> list[TuneResult]:
    risk_grid = risk_grid or [{}]
    results: list[TuneResult] = []

    for sp_over in strategy_grid:
        sp = {**base_strategy_params, **sp_over}
        for rk_over in risk_grid:
            risk_cfg = replace(base_risk, **rk_over)
            strategy = build_strategy(strategy_name, sp)
            bt = Backtester(strategy, risk_cfg, fees, trend_ratio=trend_ratio,
                            execution=execution)
            res = bt.run(candles, instrument=instrument)
            s = res.stats
            results.append(
                TuneResult(
                    params=sp_over,
                    risk=rk_over,
                    expectancy=s.expectancy,
                    win_rate=s.win_rate,
                    profit_factor=s.profit_factor,
                    closed_trades=s.closed_trades,
                    return_pct=res.return_pct,
                )
            )

    # Rank: meaningful sample first, then by expectancy.
    results.sort(
        key=lambda r: (r.closed_trades >= min_trades, r.expectancy),
        reverse=True,
    )
    return results
