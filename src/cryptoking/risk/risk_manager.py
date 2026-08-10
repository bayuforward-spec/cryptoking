"""Risk manager — the safety belt between signals and execution.

Responsibilities:
  * Position sizing from risk-per-trade and the stop distance.
  * Enforce max open positions and max position size.
  * Per-position stop-loss / take-profit checks.
  * A daily loss kill switch that halts all new entries.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..config import RiskConfig
from ..execution.broker import Position


@dataclass
class RiskDecision:
    allowed: bool
    quote_amount: float = 0.0
    reason: str = ""


class RiskManager:
    def __init__(self, risk: RiskConfig):
        self.cfg = risk
        self._day_start_equity: float | None = None
        self._halted = False

    # ----- daily loss kill switch -----

    def start_day(self, equity: float) -> None:
        self._day_start_equity = equity
        self._halted = False

    def update_equity(self, equity: float) -> None:
        if self._day_start_equity is None:
            self._day_start_equity = equity
            return
        drawdown = (self._day_start_equity - equity) / self._day_start_equity
        if drawdown >= self.cfg.max_daily_loss_pct:
            self._halted = True

    @property
    def halted(self) -> bool:
        return self._halted

    # ----- entry sizing / gating -----

    def size_entry(
        self,
        equity: float,
        price: float,
        num_open_positions: int,
        stop_price: float | None = None,
    ) -> RiskDecision:
        """Size a position so a stop-out loses ~`risk_per_trade` of equity.

        This is the guide's position-sizing formula:
            size = (equity * risk%) / stop_distance
        If the strategy supplies a real `stop_price` (placed beyond structure),
        we size from that exact distance; otherwise we fall back to the
        configured stop_loss_pct.
        """
        if self._halted:
            return RiskDecision(False, reason="daily loss limit reached — halted")
        if num_open_positions >= self.cfg.max_open_positions:
            return RiskDecision(False, reason="max open positions reached")

        if stop_price is not None and price > 0:
            stop_frac = (price - stop_price) / price
        else:
            stop_frac = self.cfg.stop_loss_pct
        if stop_frac <= 0:
            return RiskDecision(False, reason="invalid stop distance")

        risk_capital = equity * self.cfg.risk_per_trade
        quote_amount = risk_capital / stop_frac

        # Cap by max position fraction of equity.
        cap = equity * self.cfg.max_position_fraction
        quote_amount = min(quote_amount, cap)

        if quote_amount < 1.0:  # below a sensible minimum notional
            return RiskDecision(False, reason="position size below minimum")

        return RiskDecision(True, quote_amount=quote_amount, reason="ok")

    def target_for(
        self,
        entry_price: float,
        stop_price: float | None,
        signal_target: float | None = None,
    ) -> float:
        """Take-profit price.

        If the strategy supplies an explicit `signal_target` above entry (a
        Fibonacci-extension or support/resistance level, as the KJO charts
        mark), use it. Otherwise fall back to the flat reward-to-risk multiple.
        """
        if signal_target is not None and signal_target > entry_price:
            return signal_target
        if stop_price is not None:
            risk_dist = entry_price - stop_price
            return entry_price + self.cfg.rr_ratio * risk_dist
        return entry_price * (1 + self.cfg.take_profit_pct)

    def stop_for(self, entry_price: float, stop_price: float | None) -> float:
        if stop_price is not None:
            return stop_price
        return entry_price * (1 - self.cfg.stop_loss_pct)

    # ----- exit checks -----

    def exit_for_stop_or_target(self, pos: Position, price: float) -> str | None:
        """Return 'stop_loss' / 'take_profit' if an exit is triggered, else None."""
        # Prefer explicit per-position levels (set from structure at entry).
        if pos.stop_price is not None and price <= pos.stop_price:
            return "stop_loss"
        if pos.target_price is not None and price >= pos.target_price:
            return "take_profit"
        if pos.stop_price is None and pos.target_price is None:
            change = (price - pos.entry_price) / pos.entry_price
            if change <= -self.cfg.stop_loss_pct:
                return "stop_loss"
            if change >= self.cfg.take_profit_pct:
                return "take_profit"
        return None
