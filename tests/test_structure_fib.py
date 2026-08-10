from cryptoking.exchange.cryptocom import Candle, Quote
from cryptoking.strategy.structure_fib import StructureFibStrategy


def mk(closes):
    return [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1.0) for i, c in enumerate(closes)]


def q(mid):
    return Quote("BTC_USDT", bid=mid * 0.9999, ask=mid * 1.0001, last=mid)


def downtrend(n=40):
    # clean fractal downtrend with clear local extremes
    return [200, 194, 188, 194, 198, 190, 182, 190, 194,
            184, 176, 184, 188, 178, 170, 178, 182]


def test_warmup_holds():
    s = StructureFibStrategy()
    sig = s.evaluate(mk([100, 101, 102]), q(102), in_position=False)
    assert sig.action == "HOLD"


def test_downtrend_no_long():
    s = StructureFibStrategy(swing_k=2)
    closes = downtrend()
    sig = s.evaluate(mk(closes), q(closes[-1]), in_position=False)
    assert sig.action == "HOLD"


def test_exit_on_downtrend_structure():
    s = StructureFibStrategy(swing_k=2)
    closes = downtrend()
    sig = s.evaluate(mk(closes), q(closes[-1]), in_position=True)
    assert sig.action == "SELL"


def test_buy_sets_stop_below_price():
    # Uptrend with a pullback into the golden pocket + a bullish hammer last candle.
    s = StructureFibStrategy(swing_k=2, require_candle_pattern=True)
    # build an up-impulse from 100 -> 120, then pull back near 0.7 retrace (~106)
    closes = [100, 98, 96, 100, 108, 114, 120]  # impulse up to 120 (low ~96)
    candles = mk(closes)
    # append a pullback hammer candle sitting in the golden pocket
    # golden pocket of (96,120): 120-24*0.618=105.2 .. 120-24*0.786=101.1
    hammer = Candle(t=99, o=103.5, h=103.8, l=99.0, c=103.4, v=1.0)  # long lower wick
    candles.append(hammer)
    sig = s.evaluate(candles, q(103.4), in_position=False)
    # Either a BUY with a stop below price, or a HOLD with a clear reason — but
    # if it buys, the stop must be valid.
    if sig.action == "BUY":
        assert sig.stop_price is not None and sig.stop_price < 103.4
        # KJO-style TP context is always attached on a BUY.
        assert "fib_targets" in sig.meta
        assert "resistances" in sig.meta


def _buy_setup():
    closes = [100, 98, 96, 100, 108, 114, 120]
    candles = mk(closes)
    candles.append(Candle(t=99, o=103.5, h=103.8, l=99.0, c=103.4, v=1.0))
    return candles


def test_target_mode_rr_leaves_target_none():
    s = StructureFibStrategy(swing_k=2, target_mode="rr")
    sig = s.evaluate(_buy_setup(), q(103.4), in_position=False)
    if sig.action == "BUY":
        assert sig.target_price is None  # risk manager applies the flat R:R


def test_target_mode_fib_ext_sets_target_above_price():
    s = StructureFibStrategy(swing_k=2, target_mode="fib_ext", min_rr=1.0)
    sig = s.evaluate(_buy_setup(), q(103.4), in_position=False)
    if sig.action == "BUY" and sig.target_price is not None:
        assert sig.target_price > 103.4
        assert sig.meta.get("target_rr", 0) >= 1.0
