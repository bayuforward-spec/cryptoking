"""EMA-crossover + RSI scalping strategy (fee-aware).

Entry (go long) when ALL hold:
  * fast EMA > slow EMA  (short-term momentum up)
  * RSI not overbought   (room to run)
  * spread is tight       (scalping dies on wide spreads)

Exit (close long) when EITHER:
  * fast EMA crosses back below slow EMA, OR
  * RSI prints overbought (momentum exhausted)

Stop-loss / take-profit are enforced by the risk manager, not here — this
module only emits directional signals.
"""

from __future__ import annotations

from typing import Sequence

from ..exchange.cryptocom import Candle, Quote
from ..indicators import ema, rsi
from .base import Signal, Strategy


class EmaRsiScalper(Strategy):
    name = "ema_rsi_scalper"

    def __init__(
        self,
        ema_fast: int = 9,
        ema_slow: int = 21,
        rsi_period: int = 14,
        rsi_overbought: float = 70,
        rsi_oversold: float = 30,
        min_edge: float = 0.002,
        max_spread: float = 0.0008,
    ):
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.min_edge = min_edge
        self.max_spread = max_spread

    def evaluate(
        self,
        candles: Sequence[Candle],
        quote: Quote,
        in_position: bool,
        trend_candles: Sequence[Candle] | None = None,
    ) -> Signal:
        closes = [c.c for c in candles]
        need = max(self.ema_slow, self.rsi_period) + 2
        if len(closes) < need:
            return Signal("HOLD", reason="warming up (insufficient candles)")

        fast = ema(closes, self.ema_fast)
        slow = ema(closes, self.ema_slow)
        r = rsi(closes, self.rsi_period)
        if fast is None or slow is None or r is None:
            return Signal("HOLD", reason="indicators unavailable")

        meta = {
            "ema_fast": round(fast, 4),
            "ema_slow": round(slow, 4),
            "rsi": round(r, 2),
            "spread": round(quote.spread_frac, 6),
        }

        uptrend = fast > slow

        if in_position:
            # Exit on momentum reversal or exhaustion.
            if not uptrend:
                return Signal("SELL", reason="EMA cross down", meta=meta)
            if r >= self.rsi_overbought:
                return Signal("SELL", reason="RSI overbought", meta=meta)
            return Signal("HOLD", reason="holding long", meta=meta)

        # Flat: look for an entry.
        if quote.spread_frac > self.max_spread:
            return Signal("HOLD", reason="spread too wide", meta=meta)
        if not uptrend:
            return Signal("HOLD", reason="no uptrend", meta=meta)
        if r >= self.rsi_overbought:
            return Signal("HOLD", reason="RSI overbought, skip entry", meta=meta)

        # Distance of price above slow EMA as a rough edge proxy.
        edge = (fast - slow) / slow
        confidence = max(0.0, min(1.0, edge / self.min_edge))
        return Signal(
            "BUY",
            reason="EMA uptrend + RSI ok",
            confidence=confidence,
            meta=meta,
        )
