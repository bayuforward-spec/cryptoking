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
    meta: dict[str, Any] = field(default_factory=dict)


class Strategy:
    """Base class. Subclasses implement `evaluate`."""

    name = "base"

    def evaluate(
        self,
        candles: Sequence[Candle],
        quote: Quote,
        in_position: bool,
    ) -> Signal:
        raise NotImplementedError
