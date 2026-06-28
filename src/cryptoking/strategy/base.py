"""Strategy interface."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from ..exchange.cryptocom import Candle, Quote

Action = str  # "BUY" | "SELL" | "HOLD"


@dataclass
class Signal:
    action: Action = "HOLD"
    reason: str = ""
    # Optional strength in [0, 1] for future position-sizing refinements.
    confidence: float = 0.0
    # Suggested protective stop price (the guide places it beyond structure).
    # When set, the risk manager sizes the position from this stop distance.
    stop_price: float | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy:
    """Base class. Subclasses implement `evaluate`."""

    name = "base"

    def evaluate(
        self,
        candles: Sequence[Candle],
        quote: Quote,
        in_position: bool,
        trend_candles: Sequence[Candle] | None = None,
    ) -> Signal:
        """Evaluate one instrument.

        `candles` are the execution timeframe; `trend_candles` (optional) are a
        higher timeframe used for top-down direction. Strategies that don't need
        the higher timeframe can ignore it.
        """
        raise NotImplementedError
