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
    ) -> RiskDecision:
        if self._halted:
            return RiskDecision(False, reason="daily loss limit reached — halted")
        if num_open_positions >= self.cfg.max_open_positions:
            return RiskDecision(False, reason="max open positions reached")

        # Risk a fixed fraction of equity, sized so a stop-loss hit loses ~that much.
        risk_capital = equity * self.cfg.risk_per_trade
        if self.cfg.stop_loss_pct <= 0:
            return RiskDecision(False, reason="invalid stop_loss_pct")
        # quote_amount * stop_loss_pct = risk_capital
        quote_amount = risk_capital / self.cfg.stop_loss_pct

        # Cap by max position fraction of equity.
        cap = equity * self.cfg.max_position_fraction
        quote_amount = min(quote_amount, cap)

        if quote_amount < 1.0:  # below a sensible minimum notional
            return RiskDecision(False, reason="position size below minimum")

        return RiskDecision(True, quote_amount=quote_amount, reason="ok")

    # ----- exit checks -----

    def exit_for_stop_or_target(self, pos: Position, price: float) -> str | None:
        """Return 'stop_loss' / 'take_profit' if an exit is triggered, else None."""
        change = (price - pos.entry_price) / pos.entry_price
        if change <= -self.cfg.stop_loss_pct:
            return "stop_loss"
        if change >= self.cfg.take_profit_pct:
            return "take_profit"
        return None
