"""Structure + Fibonacci + candlestick strategy — a faithful encoding of the
trading guide's method.

Top-down (the guide's framework):
  * Higher timeframe (`trend_candles`) gives DIRECTION via market structure.
  * Execution timeframe (`candles`) gives the ENTRY.

The guide's three rules, for a long (spot is long-only here):
  Rule 1 — only trade WITH the structure (higher-TF must be an uptrend; not down).
  Rule 2 — only enter at support: price pulled back into the Fibonacci
           golden pocket (0.618–0.786) of the last up-impulse.
  Rule 3 — confirm with a bullish reversal candlestick, and place the stop
           just below the swing low. Risk sizing + R:R are handled downstream.

Exit: structure on the execution TF breaks to a downtrend, or a bearish
reversal candle prints. Stop-loss / take-profit (R:R) are enforced by the
risk manager via the stop_price we attach here.
"""

from __future__ import annotations

from typing import Sequence

from ..exchange.cryptocom import Candle, Quote
from ..patterns import bearish_reversal, bullish_reversal
from ..structure import (
    fib_retracement,
    last_up_impulse,
    market_structure,
)
from .base import Signal, Strategy


class StructureFibStrategy(Strategy):
    name = "structure_fib"

    def __init__(
        self,
        swing_k: int = 3,
        require_candle_pattern: bool = True,
        stop_buffer: float = 0.0015,   # place stop this fraction below swing low
        allow_range_entries: bool = False,
    ):
        self.swing_k = swing_k
        self.require_candle_pattern = require_candle_pattern
        self.stop_buffer = stop_buffer
        self.allow_range_entries = allow_range_entries

    def evaluate(
        self,
        candles: Sequence[Candle],
        quote: Quote,
        in_position: bool,
        trend_candles: Sequence[Candle] | None = None,
    ) -> Signal:
        need = 4 * self.swing_k + 5
        if len(candles) < need:
            return Signal("HOLD", reason="warming up (insufficient candles)")

        exec_struct = market_structure(candles, self.swing_k)
        # Direction comes from the higher timeframe if provided, else execution TF.
        trend_src = trend_candles if trend_candles and len(trend_candles) >= need else candles
        trend = market_structure(trend_src, self.swing_k).trend

        meta = {
            "trend": trend,
            "exec_structure": exec_struct.trend,
        }

        if in_position:
            if exec_struct.trend == "downtrend":
                return Signal("SELL", reason="structure broke to downtrend", meta=meta)
            hit, name = bearish_reversal(candles)
            if hit:
                return Signal("SELL", reason=f"bearish reversal ({name})", meta=meta)
            return Signal("HOLD", reason="holding long", meta=meta)

        # ---- Rule 1: trade with structure (need an uptrend up high) ----
        ok_trend = trend == "uptrend" or (self.allow_range_entries and trend == "range")
        if not ok_trend:
            return Signal("HOLD", reason=f"trend not long-friendly ({trend})", meta=meta)

        # ---- Rule 2: price at support — inside the golden pocket ----
        impulse = last_up_impulse(candles, self.swing_k)
        if impulse is None:
            return Signal("HOLD", reason="no clean up-impulse for fib", meta=meta)
        low, high = impulse
        fib = fib_retracement(low, high)
        price = quote.mid
        meta["golden_pocket"] = [round(fib.golden_high, 2), round(fib.golden_low, 2)]
        meta["price"] = round(price, 2)
        if not fib.in_golden_pocket(price):
            return Signal("HOLD", reason="price not in golden pocket", meta=meta)

        # ---- Rule 3: bullish candlestick confirmation + stop below swing low ----
        if self.require_candle_pattern:
            hit, name = bullish_reversal(candles)
            if not hit:
                return Signal("HOLD", reason="awaiting bullish candle", meta=meta)
            meta["pattern"] = name
        else:
            meta["pattern"] = "n/a"

        # Stop goes just below the impulse swing low (structure invalidation).
        stop_price = low * (1 - self.stop_buffer)
        if stop_price >= price:
            return Signal("HOLD", reason="stop not below price", meta=meta)

        return Signal(
            "BUY",
            reason=f"uptrend + golden pocket + {meta['pattern']}",
            confidence=0.7,
            stop_price=stop_price,
            meta=meta,
        )
