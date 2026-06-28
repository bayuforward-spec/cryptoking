from cryptoking.exchange.cryptocom import Candle
from cryptoking.structure import (
    fib_retracement,
    market_structure,
    last_up_impulse,
    GOLDEN_LOW,
    GOLDEN_HIGH,
)


def mk(closes):
    out = []
    for i, c in enumerate(closes):
        out.append(Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1.0))
    return out


def test_fib_golden_pocket():
    fib = fib_retracement(100.0, 200.0)
    assert fib.levels[0.0] == 200.0
    assert fib.levels[1.0] == 100.0
    assert fib.levels[0.5] == 150.0
    # golden pocket is between 0.618 and 0.786 retracement
    assert fib.golden_low == 200.0 - 100.0 * GOLDEN_LOW
    assert fib.golden_high == 200.0 - 100.0 * GOLDEN_HIGH
    assert fib.in_golden_pocket(135.0)
    assert not fib.in_golden_pocket(190.0)


# Clean fractal zig-zags: clear local extremes over a +/-2 window.
UPTREND = [100, 106, 112, 106, 102, 110, 118, 110, 106, 116, 124, 116, 112, 122, 130, 122, 118]
DOWNTREND = [200, 194, 188, 194, 198, 190, 182, 190, 194, 184, 176, 184, 188, 178, 170, 178, 182]


def test_uptrend_detection():
    st = market_structure(mk(UPTREND), k=2)
    assert st.trend == "uptrend"


def test_downtrend_detection():
    st = market_structure(mk(DOWNTREND), k=2)
    assert st.trend == "downtrend"


def test_last_up_impulse_found():
    closes = [100, 98, 96, 100, 105, 110, 108, 106]
    imp = last_up_impulse(mk(closes), k=2)
    assert imp is not None
    low, high = imp
    assert high > low
