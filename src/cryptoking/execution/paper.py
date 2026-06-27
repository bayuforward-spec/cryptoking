"""Paper broker: simulates fills against live prices, applying fees + slippage.

No real money moves. This is the DEFAULT and the only safe place to validate a
strategy before risking capital.
"""

from __future__ import annotations

from .broker import Broker, Fill, Position


class PaperBroker(Broker):
    def __init__(self, starting_cash: float, taker_fee: float, slippage: float):
        self._cash = float(starting_cash)
        self.taker_fee = taker_fee
        self.slippage = slippage
        self._positions: dict[str, Position] = {}

    def cash(self) -> float:
        return self._cash

    def get_position(self, instrument: str) -> Position | None:
        return self._positions.get(instrument)

    def open_positions(self) -> list[Position]:
        return list(self._positions.values())

    def buy(self, instrument: str, quote_amount: float, price: float, reason: str) -> Fill:
        if instrument in self._positions:
            raise RuntimeError(f"Already in a position for {instrument}")
        # Buyer crosses the spread up and pays fees.
        fill_price = price * (1 + self.slippage)
        spend = min(quote_amount, self._cash)
        fee = spend * self.taker_fee
        invest = spend - fee
        qty = invest / fill_price
        if qty <= 0:
            raise RuntimeError("Computed non-positive quantity")
        self._cash -= spend
        self._positions[instrument] = Position(instrument, qty, fill_price)
        return Fill(instrument, "BUY", qty, fill_price, fee, reason)

    def sell(self, instrument: str, price: float, reason: str) -> Fill:
        pos = self._positions.get(instrument)
        if pos is None:
            raise RuntimeError(f"No position to sell for {instrument}")
        fill_price = price * (1 - self.slippage)
        proceeds = pos.quantity * fill_price
        fee = proceeds * self.taker_fee
        self._cash += proceeds - fee
        qty = pos.quantity
        del self._positions[instrument]
        return Fill(instrument, "SELL", qty, fill_price, fee, reason)
