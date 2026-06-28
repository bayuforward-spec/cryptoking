"""Candlestick pattern detection (from the trading guide).

Each detector takes a list of Candle and inspects the most recent candle(s),
returning True/False. Patterns are *clues*, never standalone signals — the
strategy combines them with market structure + support/resistance (Fibonacci).
"""

from __future__ import annotations

from typing import Sequence

from .exchange.cryptocom import Candle


def _body(c: Candle) -> float:
    return abs(c.c - c.o)


def _range(c: Candle) -> float:
    return c.h - c.l


def _upper_wick(c: Candle) -> float:
    return c.h - max(c.o, c.c)


def _lower_wick(c: Candle) -> float:
    return min(c.o, c.c) - c.l


def is_bullish(c: Candle) -> bool:
    return c.c > c.o


def is_bearish(c: Candle) -> bool:
    return c.c < c.o


def bullish_engulfing(candles: Sequence[Candle]) -> bool:
    """Green candle whose body fully engulfs the prior red candle's body."""
    if len(candles) < 2:
        return False
    prev, cur = candles[-2], candles[-1]
    return (
        is_bearish(prev)
        and is_bullish(cur)
        and cur.c >= prev.o
        and cur.o <= prev.c
        and _body(cur) > _body(prev)
    )


def bearish_engulfing(candles: Sequence[Candle]) -> bool:
    if len(candles) < 2:
        return False
    prev, cur = candles[-2], candles[-1]
    return (
        is_bullish(prev)
        and is_bearish(cur)
        and cur.o >= prev.c
        and cur.c <= prev.o
        and _body(cur) > _body(prev)
    )


def hammer(candles: Sequence[Candle], wick_ratio: float = 2.0) -> bool:
    """Small body near the top, long lower wick — buyers rejected the lows."""
    c = candles[-1]
    body = _body(c)
    if body == 0 or _range(c) == 0:
        return False
    return _lower_wick(c) >= wick_ratio * body and _upper_wick(c) <= body


def shooting_star(candles: Sequence[Candle], wick_ratio: float = 2.0) -> bool:
    """Small body near the bottom, long upper wick — sellers rejected the highs."""
    c = candles[-1]
    body = _body(c)
    if body == 0 or _range(c) == 0:
        return False
    return _upper_wick(c) >= wick_ratio * body and _lower_wick(c) <= body


def doji(candles: Sequence[Candle], body_frac: float = 0.1) -> bool:
    """Open ~ close: indecision."""
    c = candles[-1]
    if _range(c) == 0:
        return False
    return _body(c) <= body_frac * _range(c)


def bullish_marubozu(candles: Sequence[Candle], wick_frac: float = 0.05) -> bool:
    """Long green body, almost no wicks — strong buying conviction."""
    c = candles[-1]
    if _range(c) == 0 or not is_bullish(c):
        return False
    return _upper_wick(c) <= wick_frac * _range(c) and _lower_wick(c) <= wick_frac * _range(c)


def tweezer_bottom(candles: Sequence[Candle], tol: float = 0.001) -> bool:
    """Two candles with matching lows — a level tested twice and held."""
    if len(candles) < 2:
        return False
    a, b = candles[-2], candles[-1]
    if a.l == 0:
        return False
    return abs(a.l - b.l) / a.l <= tol and is_bearish(a) and is_bullish(b)


def bullish_reversal(candles: Sequence[Candle]) -> tuple[bool, str]:
    """Any of the bullish reversal patterns the guide favors. Returns (hit, name)."""
    if hammer(candles):
        return True, "hammer"
    if bullish_engulfing(candles):
        return True, "bullish_engulfing"
    if tweezer_bottom(candles):
        return True, "tweezer_bottom"
    if bullish_marubozu(candles):
        return True, "bullish_marubozu"
    return False, ""


def bearish_reversal(candles: Sequence[Candle]) -> tuple[bool, str]:
    if shooting_star(candles):
        return True, "shooting_star"
    if bearish_engulfing(candles):
        return True, "bearish_engulfing"
    return False, ""
