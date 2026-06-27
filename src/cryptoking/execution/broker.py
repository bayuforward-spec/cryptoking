"""Broker interface + shared position/fill models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Fill:
    instrument: str
    side: str          # BUY | SELL
    quantity: float
    price: float
    fee: float
    reason: str = ""


@dataclass
class Position:
    instrument: str
    quantity: float       # base asset held (long only in this MVP)
    entry_price: float

    def unrealized_pnl(self, price: float) -> float:
        return (price - self.entry_price) * self.quantity

    def value(self, price: float) -> float:
        return price * self.quantity


class Broker:
    """Abstract broker. Subclasses: PaperBroker, LiveBroker."""

    def cash(self) -> float:
        raise NotImplementedError

    def get_position(self, instrument: str) -> Position | None:
        raise NotImplementedError

    def open_positions(self) -> list[Position]:
        raise NotImplementedError

    def buy(self, instrument: str, quote_amount: float, price: float, reason: str) -> Fill:
        """Spend `quote_amount` of quote currency to buy at ~`price`."""
        raise NotImplementedError

    def sell(self, instrument: str, price: float, reason: str) -> Fill:
        """Close the full position at ~`price`."""
        raise NotImplementedError

    def equity(self, prices: dict[str, float]) -> float:
        """Cash + marked-to-market value of all open positions."""
        total = self.cash()
        for pos in self.open_positions():
            px = prices.get(pos.instrument, pos.entry_price)
            total += pos.value(px)
        return total
