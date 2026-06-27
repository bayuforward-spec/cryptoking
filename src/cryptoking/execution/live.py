"""Live broker: places REAL market orders on crypto.com. Real money at risk.

This wraps the authenticated client. It intentionally keeps a local mirror of
the position it opened so the engine logic is identical to paper mode. For a
hardened deployment you would also reconcile against `private/get-open-orders`
and the account balance on every loop.
"""

from __future__ import annotations

import logging

from ..exchange.cryptocom import CryptoComClient
from .broker import Broker, Fill, Position

log = logging.getLogger("cryptoking")


class LiveBroker(Broker):
    def __init__(self, client: CryptoComClient, quote_currency: str = "USDT"):
        self.client = client
        self.quote_currency = quote_currency
        self._positions: dict[str, Position] = {}
        self._cash_cache = self._fetch_cash()

    def _fetch_cash(self) -> float:
        try:
            res = self.client.get_account_summary(self.quote_currency)
            # v1 user-balance shape: result.data[0].total_available_balance etc.
            data = res.get("data", [])
            if data:
                acct = data[0]
                return float(
                    acct.get("total_available_balance")
                    or acct.get("total_cash_balance")
                    or 0.0
                )
        except Exception as exc:  # network/format issues shouldn't crash the loop
            log.warning("Could not fetch live balance: %s", exc)
        return 0.0

    def cash(self) -> float:
        return self._cash_cache

    def get_position(self, instrument: str) -> Position | None:
        return self._positions.get(instrument)

    def open_positions(self) -> list[Position]:
        return list(self._positions.values())

    def buy(self, instrument: str, quote_amount: float, price: float, reason: str) -> Fill:
        qty = round(quote_amount / price, 6)
        log.info("LIVE BUY %s qty=%s (~%.2f %s)", instrument, qty, quote_amount, self.quote_currency)
        self.client.create_order(instrument, "BUY", "MARKET", qty)
        fill_price = price
        self._positions[instrument] = Position(instrument, qty, fill_price)
        self._cash_cache = self._fetch_cash()
        return Fill(instrument, "BUY", qty, fill_price, 0.0, reason)

    def sell(self, instrument: str, price: float, reason: str) -> Fill:
        pos = self._positions.get(instrument)
        if pos is None:
            raise RuntimeError(f"No position to sell for {instrument}")
        log.info("LIVE SELL %s qty=%s", instrument, pos.quantity)
        self.client.create_order(instrument, "SELL", "MARKET", pos.quantity)
        qty = pos.quantity
        del self._positions[instrument]
        self._cash_cache = self._fetch_cash()
        return Fill(instrument, "SELL", qty, price, 0.0, reason)
