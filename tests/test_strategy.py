from cryptoking.exchange.cryptocom import Candle, Quote
from cryptoking.strategy.scalping import EmaRsiScalper


def _candles(closes):
    return [Candle(t=i, o=c, h=c, l=c, c=c, v=1.0) for i, c in enumerate(closes)]


def _quote(mid=100.0, spread=0.0001):
    half = mid * spread / 2
    return Quote("BTC_USDT", bid=mid - half, ask=mid + half, last=mid)


def test_warmup_holds():
    s = EmaRsiScalper()
    sig = s.evaluate(_candles([100, 101]), _quote(), in_position=False)
    assert sig.action == "HOLD"


def test_uptrend_generates_buy():
    s = EmaRsiScalper(rsi_overbought=101)  # disable RSI gate for this test
    closes = [100 + i * 0.2 for i in range(60)]
    sig = s.evaluate(_candles(closes), _quote(mid=closes[-1]), in_position=False)
    assert sig.action == "BUY"


def test_wide_spread_blocks_entry():
    s = EmaRsiScalper(rsi_overbought=101)
    closes = [100 + i * 0.2 for i in range(60)]
    sig = s.evaluate(
        _candles(closes), _quote(mid=closes[-1], spread=0.01), in_position=False
    )
    assert sig.action == "HOLD"
    assert "spread" in sig.reason


def test_downtrend_exits_long():
    s = EmaRsiScalper()
    closes = [120 - i * 0.2 for i in range(60)]
    sig = s.evaluate(_candles(closes), _quote(mid=closes[-1]), in_position=True)
    assert sig.action == "SELL"
