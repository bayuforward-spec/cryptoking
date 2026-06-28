#!/usr/bin/env python3
"""CryptoKing tuner CLI — grid-search params to find a positive-edge config.

Usage:
    python optimize.py --csv data/BTC_USDT.csv
    python optimize.py --demo

Edit the grids below to widen/narrow the search. Results are ranked by
expected value, with too-thin samples (<min-trades) pushed down.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.backtest import load_candles_csv  # noqa: E402
from cryptoking.config import load_config  # noqa: E402
from cryptoking.optimize import grid, optimize  # noqa: E402

# Import the synthetic generator from the backtester CLI for --demo.
from backtest import synthetic_candles  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoKing parameter tuner")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--csv")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument("--instrument", default="BTC_USDT")
    parser.add_argument("--trend-ratio", type=int, default=16)
    parser.add_argument("--min-trades", type=int, default=20)
    parser.add_argument("--top", type=int, default=10)
    args = parser.parse_args()

    cfg = load_config(args.config)
    if args.csv:
        candles = load_candles_csv(args.csv)
    elif args.demo:
        candles = synthetic_candles()
    else:
        parser.error("provide --csv <file> or --demo")

    # ---- the search space (tune these) ----
    strategy_grid = grid(
        swing_k=[2, 3, 4],
        require_candle_pattern=[True, False],
        stop_buffer=[0.001, 0.0015, 0.003],
    )
    risk_grid = grid(
        rr_ratio=[1.5, 2.0, 3.0],
    )

    results = optimize(
        candles,
        cfg.strategy.name,
        cfg.strategy.params,
        cfg.risk,
        cfg.fees,
        strategy_grid=strategy_grid,
        risk_grid=risk_grid,
        trend_ratio=args.trend_ratio,
        execution=cfg.execution,
        min_trades=args.min_trades,
        instrument=args.instrument,
    )

    combos = len(strategy_grid) * len(risk_grid)
    print(f"\n=== Tuning {cfg.strategy.name} over {len(candles)} candles "
          f"({combos} combos) ===")
    print(f"{'EV/trade':>9}  {'win%':>5}  {'PF':>5}  {'trades':>6}  {'ret%':>7}  params")
    print("-" * 78)
    for r in results[: args.top]:
        merged = {**r.params, **r.risk}
        pf = "inf" if r.profit_factor == float("inf") else f"{r.profit_factor:.2f}"
        flag = "" if r.closed_trades >= args.min_trades else "  (thin)"
        print(f"{r.expectancy:>9.4f}  {r.win_rate*100:>5.1f}  {pf:>5}  "
              f"{r.closed_trades:>6}  {r.return_pct*100:>7.2f}  {merged}{flag}")

    best = next((r for r in results if r.closed_trades >= args.min_trades), None)
    print()
    if best and best.expectancy > 0:
        print(f"✅ Best positive-edge config: {{**{best.params}, **{best.risk}}}  "
              f"(EV ${best.expectancy:.4f}/trade over {best.closed_trades} trades)")
    else:
        print("❌ No config reached a positive edge with a meaningful sample. "
              "Widen the grid, use more/real data, or rethink the strategy.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
