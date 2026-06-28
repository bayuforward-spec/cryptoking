#!/usr/bin/env python3
"""CryptoKing self-learning runner — walk-forward re-tune and propose a config.

Usage:
    python learn.py --csv data/BTC_USDT.csv          # propose only (writes logs/proposal.json)
    python learn.py --csv data/BTC_USDT.csv --apply   # apply if the proposal promotes
    python learn.py --demo                            # offline, synthetic data
    python learn.py --csv data/BTC_USDT.csv --ai-review  # add a Claude sanity-check note

Run it on a schedule (e.g. weekly cron) on your VPS to keep adapting to recent
market behavior. Promotions require beating the CURRENT config on out-of-sample
(holdout) data, so it resists overfitting. Without --apply it only proposes;
review and approve from the dashboard, or pass --apply for autonomous adaptation.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.backtest import load_candles_csv  # noqa: E402
from cryptoking.config import load_config  # noqa: E402
from cryptoking.learn import (  # noqa: E402
    apply_proposal,
    walk_forward_retune,
    write_proposal,
)
from cryptoking.optimize import grid  # noqa: E402

from backtest import synthetic_candles  # noqa: E402


def ai_review(proposal, model: str) -> str:
    """Best-effort qualitative sanity-check of the proposal via Claude."""
    try:
        import anthropic
    except ImportError:
        return "(anthropic not installed — skipped)"
    try:
        client = anthropic.Anthropic()
        payload = {
            "promote": proposal.promote,
            "strategy_params": proposal.strategy_params,
            "risk_overrides": proposal.risk_overrides,
            "current_holdout": proposal.current_holdout.__dict__,
            "proposed_holdout": proposal.proposed_holdout.__dict__,
        }
        resp = client.messages.create(
            model=model,
            max_tokens=400,
            system=(
                "You review proposed parameter changes for a crypto trading bot. "
                "The proposal was validated on out-of-sample data. In 2-3 sentences, "
                "flag overfitting risk or sizing concerns, or confirm it looks sound. "
                "Be terse and practical."
            ),
            messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
        )
        return next((b.text for b in resp.content if b.type == "text"), "").strip()
    except Exception as exc:
        return f"(AI review failed: {exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoKing self-learning")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--csv")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--apply", action="store_true", help="apply if the proposal promotes")
    parser.add_argument("--ai-review", action="store_true", help="add a Claude sanity-check note")
    parser.add_argument("--trend-ratio", type=int, default=16)
    parser.add_argument("--train-frac", type=float, default=0.6)
    parser.add_argument("--min-trades", type=int, default=15)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.csv:
        candles = load_candles_csv(args.csv)
    elif args.demo:
        candles = synthetic_candles(2000)
    else:
        parser.error("provide --csv <file> or --demo")

    strategy_grid = grid(
        swing_k=[2, 3, 4],
        require_candle_pattern=[True, False],
        stop_buffer=[0.001, 0.0015, 0.003],
    )
    risk_grid = grid(rr_ratio=[1.5, 2.0, 3.0])

    now_iso = datetime.now(timezone.utc).isoformat()
    proposal = walk_forward_retune(
        candles, cfg, strategy_grid, risk_grid, now_iso,
        train_frac=args.train_frac, trend_ratio=args.trend_ratio, min_trades=args.min_trades,
    )

    if args.ai_review:
        proposal.ai_note = ai_review(proposal, cfg.ai.model)

    write_proposal(proposal)

    print(f"\n=== Walk-forward re-tune ({len(candles)} candles) ===")
    print(f"promote: {proposal.promote}")
    print(f"reason : {proposal.reason}")
    c, p = proposal.current_holdout, proposal.proposed_holdout
    print(f"current holdout : EV {c.expectancy:+.4f}  win {c.win_rate*100:.0f}%  trades {c.closed_trades}")
    print(f"proposed holdout: EV {p.expectancy:+.4f}  win {p.win_rate*100:.0f}%  trades {p.closed_trades}")
    if proposal.promote:
        print(f"proposed change : strategy={proposal.strategy_params}  risk={proposal.risk_overrides}")
    if proposal.ai_note:
        print(f"AI note         : {proposal.ai_note}")

    if args.apply and proposal.promote:
        apply_proposal(proposal, cfg, args.config)
        write_proposal(proposal)
        print("\n✅ Applied to config.yaml. Restart the bot to use the new config.")
    elif proposal.promote:
        print("\nProposal written to logs/proposal.json. Approve from the dashboard or rerun with --apply.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
