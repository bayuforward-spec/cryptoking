from cryptoking.exchange.cryptocom import Candle
from cryptoking.patterns import (
    bullish_engulfing,
    bearish_engulfing,
    hammer,
    shooting_star,
    doji,
    bullish_marubozu,
    bullish_reversal,
)


def C(o, h, l, c):
    return Candle(t=0, o=o, h=h, l=l, c=c, v=1.0)


def test_bullish_engulfing():
    prev = C(100, 101, 98, 99)      # red
    cur = C(98, 103, 97.5, 102)     # green, body engulfs prev body
    assert bullish_engulfing([prev, cur])
    assert not bearish_engulfing([prev, cur])


def test_bearish_engulfing():
    prev = C(99, 102, 98, 101)      # green
    cur = C(101.5, 102, 96, 98)     # red engulfs
    assert bearish_engulfing([prev, cur])


def test_hammer():
    # small body at top, tiny upper wick, long lower wick
    h = C(100, 100.3, 96, 100.2)
    assert hammer([h])
    assert not shooting_star([h])


def test_shooting_star():
    assert shooting_star([C(100, 104, 99.95, 100.1)])


def test_doji():
    assert doji([C(100, 102, 98, 100.05)])
    assert not doji([C(100, 101, 99, 100.9)])


def test_marubozu_and_reversal_helper():
    assert bullish_marubozu([C(100, 105.0, 100.0, 105.0)])
    hit, name = bullish_reversal([C(100, 100.3, 96, 100.2)])
    assert hit and name == "hammer"
