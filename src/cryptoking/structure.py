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

# Fibonacci EXTENSION ratios — projected ABOVE the impulse high, used by the
# KJO Academy charts as take-profit targets (e.g. the "1.618", "2.618" TP
# labels on the AAVE / HYPE setups).
FIB_EXT_RATIOS = [1.272, 1.618, 2.0, 2.618]


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


def fib_extension(low: float, high: float, ratios: Sequence[float] = FIB_EXT_RATIOS) -> list[float]:
    """Fibonacci extension targets of an up-impulse, projected above `high`.

    Extension price = low + span * ratio (ratio > 1), i.e. the impulse leg
    measured forward. These are the TP targets the KJO charts label 1.618 /
    2.618, etc. Returns prices in ascending order.
    """
    span = high - low
    return [low + span * r for r in ratios]


@dataclass
class Level:
    price: float
    touches: int
    kind: str  # "support" | "resistance" (relative to a reference price)


def support_resistance(
    candles: Sequence[Candle],
    k: int = 3,
    tol: float = 0.005,
) -> list[Level]:
    """Cluster swing points into horizontal support/resistance levels.

    The KJO setups draw several horizontal lines (the white price labels) and
    use them both as pullback references and as take-profit targets. Here we
    take fractal swing highs/lows and merge any within `tol` (fractional price
    distance) into one level, weighting by how many swings touched it — a level
    tested more often is stronger. `kind` is left unset ("") until compared to a
    reference price by :func:`levels_relative_to`.
    """
    pts = swing_points(candles, k)
    prices = sorted(p.price for p in pts)
    if not prices:
        return []
    clusters: list[list[float]] = [[prices[0]]]
    for p in prices[1:]:
        anchor = clusters[-1][0]
        if anchor > 0 and abs(p - anchor) / anchor <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    levels: list[Level] = []
    for c in clusters:
        levels.append(Level(price=sum(c) / len(c), touches=len(c), kind=""))
    return levels


def levels_relative_to(levels: Sequence[Level], price: float) -> list[Level]:
    """Tag levels as support (<= price) or resistance (> price) for a reference."""
    out: list[Level] = []
    for lv in levels:
        out.append(Level(lv.price, lv.touches, "resistance" if lv.price > price else "support"))
    return out


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
