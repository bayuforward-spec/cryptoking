#!/usr/bin/env python3
"""CryptoKing market scanner CLI.

Ranks a watchlist of large-cap coins by the structure_fib strategy, using live
crypto.com candles — the same data the bot trades on.

Usage:
    python scan.py                       # default watchlist
    python scan.py --instruments BTC_USDT ETH_USDT SOL_USDT
    python scan.py --exec 15m --trend 4h
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from cryptoking.config import load_config  # noqa: E402
from cryptoking.exchange.cryptocom import CryptoComClient  # noqa: E402
from cryptoking.scanner import DEFAULT_WATCHLIST, scan_market  # noqa: E402


def fmt(x, d=4):
    if x is None:
        return "—"
    return f"{x:,.{d}f}"


def main() -> int:
    p = argparse.ArgumentParser(description="CryptoKing market scanner")
    p.add_argument("--config", default="config.yaml")
    p.add_argument("--instruments", nargs="+", default=DEFAULT_WATCHLIST)
    p.add_argument("--exec", dest="exec_tf", default=None, help="execution timeframe (default from config)")
    p.add_argument("--trend", dest="trend_tf", default=None, help="trend timeframe (default from config)")
    args = p.parse_args()

    cfg = load_config(args.config)
    exec_tf = args.exec_tf or cfg.engine.timeframe
    trend_tf = args.trend_tf or (cfg.engine.trend_timeframe or cfg.engine.timeframe)

    client = CryptoComClient(cfg.api_base)
    rows = scan_market(client, args.instruments, exec_tf, trend_tf)

    print(f"\n=== Market scan ({exec_tf} entry / {trend_tf} trend) ===")
    print(f"{'Coin':<12}{'Price':>14}{'Trend':>11}{'Pocket':>8}{'Candle':>14}"
          f"{'Entry':>14}{'SL':>14}{'TP1':>14}{'TP2':>14}{'Risk%':>8}{'Score':>7}")
    print("-" * 142)
    best = None
    for r in rows:
        if r.error:
            print(f"{r.instrument:<12}{'ERROR: ' + r.error}")
            continue
        if r.actionable and best is None:
            best = r
        print(f"{r.instrument:<12}{fmt(r.price):>14}{r.trend:>11}"
              f"{('yes' if r.in_pocket else '-'):>8}{(r.candle or '-'):>14}"
              f"{fmt(r.entry):>14}{fmt(r.stop):>14}{fmt(r.tp1):>14}{fmt(r.tp2):>14}"
              f"{(f'{r.risk_pct:.2f}' if r.risk_pct is not None else '-'):>8}{r.score:>7}")

    print()
    if best:
        print(f"⭐ Most potential: {best.instrument} — uptrend + golden pocket + {best.candle} "
              f"(score {best.score}/100, R:R {best.rr}:1)")
        print(f"   Entry {fmt(best.entry)}  SL {fmt(best.stop)}  TP1 {fmt(best.tp1)}  TP2 {fmt(best.tp2)}")
    else:
        print("No qualifying LONG setup right now (need uptrend + golden pocket + bullish candle). "
              "Per the rules: WAIT / stay in cash.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
