"""Market structure & Fibonacci — the technical-analysis core of the guide.

- Swing points -> trend classification (higher-highs/higher-lows = uptrend).
- Fibonacci retracement of the last impulse leg, with the 0.618–0.786
  "golden pocket" the guide uses to locate pullback entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from .exchange.cryptocom import Candle

# Standard retracement ratios from the guide.
FIB_RATIOS = [0.0, 0.236, 0.5, 0.618, 0.786, 1.0]
GOLDEN_LOW, GOLDEN_HIGH = 0.618, 0.786


@dataclass
class SwingPoint:
    index: int
    price: float
    kind: str  # "high" | "low"


@dataclass
class Structure:
    trend: str          # "uptrend" | "downtrend" | "range"
    last_high: float | None
    last_low: float | None
    swing_high_idx: int | None
    swing_low_idx: int | None


def swing_points(candles: Sequence[Candle], k: int = 3) -> list[SwingPoint]:
    """Fractal swing points: a high/low that is the extreme of a +/-k window."""
    pts: list[SwingPoint] = []
    n = len(candles)
    for i in range(k, n - k):
        window = candles[i - k : i + k + 1]
        c = candles[i]
        if c.h == max(w.h for w in window):
            pts.append(SwingPoint(i, c.h, "high"))
        if c.l == min(w.l for w in window):
            pts.append(SwingPoint(i, c.l, "low"))
    return pts


def market_structure(candles: Sequence[Candle], k: int = 3) -> Structure:
    """Classify trend from the last two swing highs and lows."""
    pts = swing_points(candles, k)
    highs = [p for p in pts if p.kind == "high"]
    lows = [p for p in pts if p.kind == "low"]

    last_high = highs[-1].price if highs else None
    last_low = lows[-1].price if lows else None
    sh_idx = highs[-1].index if highs else None
    sl_idx = lows[-1].index if lows else None

    trend = "range"
    if len(highs) >= 2 and len(lows) >= 2:
        higher_high = highs[-1].price > highs[-2].price
        higher_low = lows[-1].price > lows[-2].price
        lower_high = highs[-1].price < highs[-2].price
        lower_low = lows[-1].price < lows[-2].price
        if higher_high and higher_low:
            trend = "uptrend"
        elif lower_high and lower_low:
            trend = "downtrend"

    return Structure(trend, last_high, last_low, sh_idx, sl_idx)


@dataclass
class Fib:
    low: float            # impulse start (swing low for an up-move)
    high: float           # impulse end (swing high)
    levels: dict[float, float]
    golden_low: float     # price at 0.618 retracement (deeper)
    golden_high: float    # price at 0.786 retracement (deeper)

    def in_golden_pocket(self, price: float) -> bool:
        lo, hi = sorted((self.golden_low, self.golden_high))
        return lo <= price <= hi


def fib_retracement(low: float, high: float) -> Fib:
    """Retracement levels of an up-impulse from `low` to `high`.

    Level price = high - (high - low) * ratio, so ratio 0 = high, 1 = low.
    The golden pocket (0.618–0.786) is the deep-pullback entry zone.
    """
    span = high - low
    levels = {r: high - span * r for r in FIB_RATIOS}
    return Fib(
        low=low,
        high=high,
        levels=levels,
        golden_low=high - span * GOLDEN_LOW,
        golden_high=high - span * GOLDEN_HIGH,
    )


def last_up_impulse(candles: Sequence[Candle], k: int = 3) -> tuple[float, float] | None:
    """Find the most recent up-leg: last swing low followed by a later swing high."""
    pts = swing_points(candles, k)
    if len(pts) < 2:
        return None
    # Walk backwards for the latest high that has a low before it.
    highs = [p for p in pts if p.kind == "high"]
    lows = [p for p in pts if p.kind == "low"]
    if not highs or not lows:
        return None
    high = highs[-1]
    lows_before = [p for p in lows if p.index < high.index]
    if not lows_before:
        return None
    low = lows_before[-1]
    if high.price <= low.price:
        return None
    return low.price, high.price
