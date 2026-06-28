"""The trading engine: the 24/7 loop wiring data -> strategy -> risk -> broker."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone

from .config import Config
from .exchange.cryptocom import CryptoComClient, Quote
from .execution.broker import Broker, Fill
from .execution.live import LiveBroker
from .execution.paper import PaperBroker
from .logger import TradeLedger
from .risk.risk_manager import RiskManager
from .strategy import build_strategy

log = logging.getLogger("cryptoking")


class Engine:
    def __init__(self, config: Config):
        self.cfg = config
        self.client = CryptoComClient(
            api_base=config.api_base,
            api_key=config.api_key,
            api_secret=config.api_secret,
        )
        self.strategy = build_strategy(config.strategy.name, config.strategy.params)
        self.risk = RiskManager(config.risk)
        self.ledger = TradeLedger(config.logging.trades_csv)
        self.broker: Broker = self._build_broker()
        self.realized_pnl = 0.0
        # entry cost basis per instrument, for realized PnL accounting
        self._cost_basis: dict[str, float] = {}

        # --- live state for the web dashboard ---
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self.started_at: str | None = None
        self.last_update: str | None = None
        self.last_error: str | None = None
        self.steps = 0
        self.trades_count = 0
        self.last_signals: dict[str, dict] = {}
        self.last_prices: dict[str, float] = {}

    def _build_broker(self) -> Broker:
        if self.cfg.is_live:
            log.warning("⚠️  LIVE MODE — real orders with real money.")
            return LiveBroker(self.client, self.cfg.engine.quote_currency)
        log.info("Paper mode — simulated fills, no real money.")
        return PaperBroker(
            starting_cash=self.cfg.risk.starting_capital,
            taker_fee=self.cfg.fees.taker_fee,
            slippage=self.cfg.fees.slippage,
        )

    # ----------------------- main loop -----------------------

    def run(self) -> None:
        instruments = self.cfg.engine.instruments
        log.info(
            "Starting CryptoKing | mode=%s | instruments=%s | strategy=%s",
            self.cfg.mode,
            instruments,
            self.cfg.strategy.name,
        )
        prices = self._mark_prices()
        self.risk.start_day(self.broker.equity(prices))
        self.started_at = datetime.now(timezone.utc).isoformat()
        self._stop.clear()

        while not self._stop.is_set():
            try:
                self.step()
            except KeyboardInterrupt:
                log.info("Interrupted — shutting down.")
                break
            except Exception as exc:  # never let one bad loop kill the bot
                self.last_error = str(exc)
                log.exception("Loop error: %s", exc)
            # Sleep in small slices so stop() is responsive.
            self._stop.wait(self.cfg.engine.poll_interval_seconds)

    def stop(self) -> None:
        """Signal the run loop to exit after the current iteration."""
        self._stop.set()

    @property
    def is_running(self) -> bool:
        return self.started_at is not None and not self._stop.is_set()

    def step(self) -> None:
        """One evaluation pass across all instruments. Separated for testing."""
        prices: dict[str, float] = {}
        quotes: dict[str, Quote] = {}

        for inst in self.cfg.engine.instruments:
            quote = self.client.get_quote(inst)
            candles = self.client.get_candles(inst, self.cfg.engine.timeframe)
            trend_candles = None
            if self.cfg.engine.trend_timeframe:
                trend_candles = self.client.get_candles(
                    inst, self.cfg.engine.trend_timeframe
                )
            quotes[inst] = quote
            prices[inst] = quote.mid

            pos = self.broker.get_position(inst)
            signal = self.strategy.evaluate(
                candles, quote, in_position=pos is not None, trend_candles=trend_candles
            )
            self.last_signals[inst] = {
                "action": signal.action,
                "reason": signal.reason,
                "meta": signal.meta,
            }

            if pos is not None:
                # Risk-based exits take priority over strategy exits.
                trigger = self.risk.exit_for_stop_or_target(pos, quote.mid)
                if trigger:
                    self._close(inst, quote.mid, trigger)
                    continue
                if signal.action == "SELL":
                    self._close(inst, quote.mid, signal.reason)
                continue

            if signal.action == "BUY":
                equity = self.broker.equity(prices)
                decision = self.risk.size_entry(
                    equity,
                    quote.mid,
                    len(self.broker.open_positions()),
                    stop_price=signal.stop_price,
                )
                if decision.allowed:
                    self._open(
                        inst, decision.quote_amount, quote.mid,
                        signal.reason, signal.stop_price,
                    )
                else:
                    log.debug("Entry blocked for %s: %s", inst, decision.reason)

        equity = self.broker.equity(prices)
        self.risk.update_equity(equity)
        if self.risk.halted:
            log.warning("Daily loss kill switch ACTIVE — no new entries today.")

        with self._lock:
            self.last_prices = prices
            self.last_update = datetime.now(timezone.utc).isoformat()
            self.steps += 1

    def snapshot(self) -> dict:
        """Thread-safe view of bot state for the web dashboard."""
        with self._lock:
            prices = dict(self.last_prices)
            positions = []
            for pos in self.broker.open_positions():
                px = prices.get(pos.instrument, pos.entry_price)
                positions.append(
                    {
                        "instrument": pos.instrument,
                        "quantity": pos.quantity,
                        "entry_price": pos.entry_price,
                        "current_price": px,
                        "stop_price": pos.stop_price,
                        "target_price": pos.target_price,
                        "unrealized_pnl": pos.unrealized_pnl(px),
                    }
                )
            return {
                "mode": self.cfg.mode,
                "running": self.is_running,
                "halted": self.risk.halted,
                "started_at": self.started_at,
                "last_update": self.last_update,
                "last_error": self.last_error,
                "steps": self.steps,
                "trades_count": self.trades_count,
                "strategy": self.cfg.strategy.name,
                "instruments": self.cfg.engine.instruments,
                "cash": self.broker.cash(),
                "equity": self.broker.equity(prices),
                "realized_pnl": self.realized_pnl,
                "prices": prices,
                "positions": positions,
                "signals": dict(self.last_signals),
            }

    # ----------------------- order helpers -----------------------

    def _open(
        self,
        inst: str,
        quote_amount: float,
        price: float,
        reason: str,
        stop_price: float | None = None,
    ) -> None:
        fill = self.broker.buy(inst, quote_amount, price, reason)
        self._cost_basis[inst] = fill.quantity * fill.price + fill.fee
        # Attach structure-based stop + R:R target to the open position.
        pos = self.broker.get_position(inst)
        if pos is not None:
            pos.stop_price = self.risk.stop_for(fill.price, stop_price)
            pos.target_price = self.risk.target_for(fill.price, stop_price)
        self._record(fill, realized=0.0)
        log.info(
            "OPEN  %s qty=%.6f @ %.2f stop=%.2f target=%.2f (%s)",
            inst, fill.quantity, fill.price,
            pos.stop_price if pos else 0.0, pos.target_price if pos else 0.0, reason,
        )

    def _close(self, inst: str, price: float, reason: str) -> None:
        fill = self.broker.sell(inst, price, reason)
        proceeds = fill.quantity * fill.price - fill.fee
        basis = self._cost_basis.pop(inst, fill.quantity * fill.price)
        pnl = proceeds - basis
        self.realized_pnl += pnl
        self._record(fill, realized=pnl)
        log.info(
            "CLOSE %s qty=%.6f @ %.2f fee=%.4f pnl=%.4f (%s)",
            inst, fill.quantity, fill.price, fill.fee, pnl, reason,
        )

    def _record(self, fill: Fill, realized: float) -> None:
        self.trades_count += 1
        self.ledger.record(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "mode": self.cfg.mode,
                "instrument": fill.instrument,
                "side": fill.side,
                "quantity": f"{fill.quantity:.8f}",
                "price": f"{fill.price:.4f}",
                "fee": f"{fill.fee:.6f}",
                "reason": fill.reason,
                "realized_pnl": f"{realized:.6f}",
                "equity": f"{self.broker.cash():.4f}",
            }
        )

    def _mark_prices(self) -> dict[str, float]:
        prices: dict[str, float] = {}
        for inst in self.cfg.engine.instruments:
            try:
                prices[inst] = self.client.get_quote(inst).mid
            except Exception as exc:
                log.warning("Could not fetch price for %s: %s", inst, exc)
        return prices
