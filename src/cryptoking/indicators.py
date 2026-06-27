"""Pure-Python technical indicators (no numpy/pandas dependency)."""

from __future__ import annotations

from typing import Sequence


def sma(values: Sequence[float], period: int) -> float | None:
    """Simple moving average of the last `period` values."""
    if len(values) < period or period <= 0:
        return None
    return sum(values[-period:]) / period


def ema(values: Sequence[float], period: int) -> float | None:
    """Exponential moving average. Seeded with the SMA of the first window."""
    if len(values) < period or period <= 0:
        return None
    k = 2 / (period + 1)
    # Seed with SMA of the first `period` values, then walk forward.
    e = sum(values[:period]) / period
    for v in values[period:]:
        e = v * k + e * (1 - k)
    return e


def rsi(values: Sequence[float], period: int = 14) -> float | None:
    """Relative Strength Index using Wilder's smoothing."""
    if len(values) <= period or period <= 0:
        return None

    gains = 0.0
    losses = 0.0
    # Initial average gain/loss over the first `period` deltas.
    for i in range(1, period + 1):
        delta = values[i] - values[i - 1]
        if delta >= 0:
            gains += delta
        else:
            losses -= delta
    avg_gain = gains / period
    avg_loss = losses / period

    # Wilder smoothing across the remaining deltas.
    for i in range(period + 1, len(values)):
        delta = values[i] - values[i - 1]
        gain = max(delta, 0.0)
        loss = max(-delta, 0.0)
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))
