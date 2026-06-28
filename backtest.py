#!/usr/bin/env python3
"""CryptoKing backtester CLI — prove the edge before risking money.

Usage:
    python backtest.py --csv data/BTC_USDT_15m.csv          # real data
    python backtest.py --demo                                # synthetic data
    python backtest.py --csv data.csv --instrument ETH_USDT

CSV format: header row with columns t,o,h,l,c,v (t = open time in ms).
You can fetch candles via the crypto.com MCP and save them in this format.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.backtest import Backtester, load_candles_csv  # noqa: E402
from cryptoking.config import load_config  # noqa: E402
from cryptoking.exchange.cryptocom import Candle  # noqa: E402
from cryptoking.strategy import build_strategy  # noqa: E402


def synthetic_candles(n: int = 1500, seed_base: float = 100.0) -> list[Candle]:
    """Deterministic trending+oscillating series (no RNG — reproducible).

    Layered sine waves create repeated up-impulses and pullbacks so the
    selective structure_fib strategy gets enough setups to be illustrative.
    """
    candles = []
    price = seed_base
    for i in range(n):
        trend = i * 0.03                      # gentle long-term uptrend bias
        swing = math.sin(i / 18) * 6          # medium impulses + pullbacks
        wiggle = math.sin(i / 4) * 1.0 + math.sin(i / 2) * 0.5
        close = seed_base + trend + swing + wiggle
        open_ = price
        high = max(open_, close) + abs(math.sin(i / 5)) * 0.6
        low = min(open_, close) - abs(math.cos(i / 5)) * 0.6
        candles.append(Candle(t=i * 900_000, o=open_, h=high, l=low, c=close, v=1.0))
        price = close
    return candles


def main() -> int:
    parser = argparse.ArgumentParser(description="CryptoKing backtester")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--csv", help="path to OHLCV CSV (t,o,h,l,c,v)")
    parser.add_argument("--demo", action="store_true", help="use synthetic data")
    parser.add_argument("--fetch", metavar="OUT.csv",
                        help="fetch live candles from crypto.com and save to this CSV, then exit")
    parser.add_argument("--instrument", default="BTC_USDT")
    parser.add_argument("--trend-ratio", type=int, default=16,
                        help="how many exec candles aggregate into 1 trend candle")
    args = parser.parse_args()

    cfg = load_config(args.config)

    if args.fetch:
        import csv as _csv
        from cryptoking.exchange.cryptocom import CryptoComClient
        client = CryptoComClient(cfg.api_base)
        candles = client.get_candles(args.instrument, cfg.engine.timeframe)
        out = Path(args.fetch)
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", newline="", encoding="utf-8") as fh:
            w = _csv.writer(fh)
            w.writerow(["t", "o", "h", "l", "c", "v"])
            for c in candles:
                w.writerow([c.t, c.o, c.h, c.l, c.c, c.v])
        print(f"Saved {len(candles)} {cfg.engine.timeframe} candles for "
              f"{args.instrument} -> {out}")
        return 0

    if args.csv:
        candles = load_candles_csv(args.csv)
        source = args.csv
    elif args.demo:
        candles = synthetic_candles()
        source = "synthetic"
    else:
        parser.error("provide --csv <file> or --demo")

    strategy = build_strategy(cfg.strategy.name, cfg.strategy.params)
    bt = Backtester(strategy, cfg.risk, cfg.fees, trend_ratio=args.trend_ratio,
                    execution=cfg.execution)
    result = bt.run(candles, instrument=args.instrument)
    s = result.stats

    print(f"\n=== Backtest: {cfg.strategy.name} on {args.instrument} ({source}) ===")
    print(f"candles            : {len(candles)}")
    print(f"starting equity    : ${result.starting_equity:,.2f}")
    print(f"final equity       : ${result.final_equity:,.2f}")
    print(f"return             : {result.return_pct*100:+.2f}%")
    print(f"closed trades      : {s.closed_trades}  ({s.wins}W / {s.losses}L)")
    print(f"win rate           : {s.win_rate*100:.1f}%")
    print(f"avg win / avg loss : ${s.avg_win:.4f} / ${s.avg_loss:.4f}")
    print(f"reward : risk      : {s.reward_risk:.2f}")
    print(f"profit factor      : {s.profit_factor:.2f}")
    print(f"expected value/trade: ${s.expectancy:.4f}   "
          f"{'(POSITIVE EDGE ✅)' if s.expectancy > 0 else '(no edge ❌)'}")
    print()
    if s.closed_trades < 30:
        print("⚠️  Fewer than 30 trades — not statistically meaningful yet. "
              "Use more data before trusting these numbers.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
