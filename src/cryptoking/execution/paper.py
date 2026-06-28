"""Paper broker: simulates fills against live prices, applying fees + slippage.

Supports two order styles (the guide / fee-reduction work):
  * market (taker) — crosses the spread, pays the taker fee + slippage.
  * limit  (maker) — posts inside the spread, pays the lower maker fee and
    (modeled as) no slippage. This is the cheaper path for frequent trading.

No real money moves. This is the DEFAULT and the only safe place to validate a
strategy before risking capital.
"""

from __future__ import annotations

from .broker import Broker, Fill, Position


class PaperBroker(Broker):
    def __init__(
        self,
        starting_cash: float,
        taker_fee: float,
        slippage: float,
        maker_fee: float | None = None,
        order_type: str = "market",
        limit_offset: float = 0.0005,
    ):
        self._cash = float(starting_cash)
        self.taker_fee = taker_fee
        self.maker_fee = maker_fee if maker_fee is not None else taker_fee
        self.slippage = slippage
        self.order_type = order_type
        self.limit_offset = limit_offset
        self._positions: dict[str, Position] = {}

    @property
    def _is_maker(self) -> bool:
        return self.order_type.lower() == "limit"

    def _fee_rate(self) -> float:
        return self.maker_fee if self._is_maker else self.taker_fee

    def cash(self) -> float:
        return self._cash

    def get_position(self, instrument: str) -> Position | None:
        return self._positions.get(instrument)

    def open_positions(self) -> list[Position]:
        return list(self._positions.values())

    def buy(self, instrument: str, quote_amount: float, price: float, reason: str) -> Fill:
        if instrument in self._positions:
            raise RuntimeError(f"Already in a position for {instrument}")
        # Maker posts a touch below mid (no spread cross); taker crosses up.
        if self._is_maker:
            fill_price = price * (1 - self.limit_offset)
        else:
            fill_price = price * (1 + self.slippage)
        spend = min(quote_amount, self._cash)
        fee = spend * self._fee_rate()
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
        if self._is_maker:
            fill_price = price * (1 + self.limit_offset)
        else:
            fill_price = price * (1 - self.slippage)
        proceeds = pos.quantity * fill_price
        fee = proceeds * self._fee_rate()
        self._cash += proceeds - fee
        qty = pos.quantity
        del self._positions[instrument]
        return Fill(instrument, "SELL", qty, fill_price, fee, reason)
