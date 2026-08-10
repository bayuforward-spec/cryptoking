"""Backtester — replay historical candles through the SAME strategy + risk +
paper-broker logic the live engine uses, then report the edge (the guide's
step 1 before risking money).

Single data source: you provide execution-timeframe candles. The higher
"trend" timeframe is built by aggregating them (`trend_ratio`), so top-down
analysis works without a second feed.

Exits are checked intrabar against each candle's high/low, which is more
realistic than close-only fills.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

from .analytics import Stats, stats_from_pnls
from .config import ExecutionConfig, FeesConfig, RiskConfig
from .exchange.cryptocom import Candle, Quote
from .execution.paper import PaperBroker
from .risk.risk_manager import RiskManager
from .strategy.base import Strategy


@dataclass
class BacktestResult:
    stats: Stats
    starting_equity: float
    final_equity: float
    trades: list[dict] = field(default_factory=list)
    equity_curve: list[float] = field(default_factory=list)

    @property
    def return_pct(self) -> float:
        if self.starting_equity <= 0:
            return 0.0
        return (self.final_equity - self.starting_equity) / self.starting_equity


def aggregate_candles(candles: Sequence[Candle], ratio: int) -> list[Candle]:
    """Aggregate `ratio` execution candles into one higher-timeframe candle."""
    if ratio <= 1:
        return list(candles)
    out: list[Candle] = []
    for i in range(0, len(candles), ratio):
        chunk = candles[i : i + ratio]
        if not chunk:
            continue
        out.append(
            Candle(
                t=chunk[0].t,
                o=chunk[0].o,
                h=max(c.h for c in chunk),
                l=min(c.l for c in chunk),
                c=chunk[-1].c,
                v=sum(c.v for c in chunk),
            )
        )
    return out


class Backtester:
    def __init__(
        self,
        strategy: Strategy,
        risk_cfg: RiskConfig,
        fees: FeesConfig,
        trend_ratio: int = 16,
        execution: ExecutionConfig | None = None,
    ):
        self.strategy = strategy
        self.risk_cfg = risk_cfg
        self.fees = fees
        self.trend_ratio = trend_ratio
        self.execution = execution or ExecutionConfig()

    def run(
        self,
        candles: Sequence[Candle],
        instrument: str = "BTC_USDT",
        warmup: int = 60,
    ) -> BacktestResult:
        broker = PaperBroker(
            self.risk_cfg.starting_capital,
            self.fees.taker_fee,
            self.fees.slippage,
            maker_fee=self.fees.maker_fee,
            order_type=self.execution.order_type,
            limit_offset=self.execution.limit_offset,
        )
        risk = RiskManager(self.risk_cfg)
        start_equity = self.risk_cfg.starting_capital
        risk.start_day(start_equity)

        pnls: list[float] = []
        trades: list[dict] = []
        equity_curve: list[float] = []
        cost_basis: dict[str, float] = {}

        n = len(candles)
        start = max(warmup, self.trend_ratio)
        for i in range(start, n):
            window = candles[: i + 1]
            cur = candles[i]
            price = cur.c
            quote = Quote(instrument, bid=price, ask=price, last=price)
            trend_candles = aggregate_candles(window, self.trend_ratio)

            pos = broker.get_position(instrument)

            # 1) Intrabar protective exits for an open position.
            if pos is not None:
                exit_price = None
                reason = ""
                if pos.stop_price is not None and cur.l <= pos.stop_price:
                    exit_price, reason = pos.stop_price, "stop_loss"
                elif pos.target_price is not None and cur.h >= pos.target_price:
                    exit_price, reason = pos.target_price, "take_profit"
                if exit_price is not None:
                    pnl = self._close(broker, instrument, exit_price, reason, cost_basis, trades)
                    pnls.append(pnl)
                    pos = None

            # 2) Strategy evaluation on the close.
            signal = self.strategy.evaluate(
                window, quote, in_position=pos is not None, trend_candles=trend_candles
            )

            if pos is not None and signal.action == "SELL":
                pnl = self._close(broker, instrument, price, signal.reason, cost_basis, trades)
                pnls.append(pnl)
            elif pos is None and signal.action == "BUY":
                equity = broker.equity({instrument: price})
                decision = risk.size_entry(
                    equity, price, len(broker.open_positions()), stop_price=signal.stop_price
                )
                if decision.allowed:
                    fill = broker.buy(instrument, decision.quote_amount, price, signal.reason)
                    cost_basis[instrument] = fill.quantity * fill.price + fill.fee
                    p = broker.get_position(instrument)
                    p.stop_price = risk.stop_for(fill.price, signal.stop_price)
                    p.target_price = risk.target_for(fill.price, signal.stop_price, signal.target_price)
                    trades.append(
                        {"side": "BUY", "price": fill.price, "qty": fill.quantity,
                         "reason": signal.reason, "pnl": 0.0}
                    )

            eq = broker.equity({instrument: price})
            risk.update_equity(eq)
            equity_curve.append(eq)

        final_equity = equity_curve[-1] if equity_curve else start_equity
        return BacktestResult(
            stats=stats_from_pnls(pnls),
            starting_equity=start_equity,
            final_equity=final_equity,
            trades=trades,
            equity_curve=equity_curve,
        )

    def _close(self, broker, instrument, price, reason, cost_basis, trades) -> float:
        fill = broker.sell(instrument, price, reason)
        proceeds = fill.quantity * fill.price - fill.fee
        basis = cost_basis.pop(instrument, fill.quantity * fill.price)
        pnl = proceeds - basis
        trades.append(
            {"side": "SELL", "price": fill.price, "qty": fill.quantity,
             "reason": reason, "pnl": pnl}
        )
        return pnl


# ----------------------- data loading -----------------------

def load_candles_csv(path: str) -> list[Candle]:
    """Load OHLCV candles from a CSV with columns t,o,h,l,c,v (header required)."""
    out: list[Candle] = []
    with Path(path).open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            out.append(
                Candle(
                    t=int(float(row["t"])),
                    o=float(row["o"]),
                    h=float(row["h"]),
                    l=float(row["l"]),
                    c=float(row["c"]),
                    v=float(row.get("v", 0) or 0),
                )
            )
    out.sort(key=lambda c: c.t)
    return out
