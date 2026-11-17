from cryptoking.exchange.cryptocom import Candle, Quote
from cryptoking.scanner import scan_instrument, scan_market


class StubClient:
    def __init__(self, exec_closes, trend_closes, mid):
        self._ex = [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1) for i, c in enumerate(exec_closes)]
        self._tr = [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1) for i, c in enumerate(trend_closes)]
        self._mid = mid

    def get_quote(self, inst):
        return Quote(inst, bid=self._mid * 0.9999, ask=self._mid * 1.0001, last=self._mid)

    def get_candles(self, inst, tf):
        # longer series = trend timeframe in these tests
        return self._tr if len(self._tr) >= len(self._ex) and tf == "4h" else self._ex


UP = [100, 106, 112, 106, 102, 110, 118, 110, 106, 116, 124, 116, 112, 122, 130, 122, 118]
DOWN = [200, 194, 188, 194, 198, 190, 182, 190, 194, 184, 176, 184, 188, 178, 170, 178, 182]


def test_downtrend_not_actionable():
    client = StubClient(DOWN, DOWN, DOWN[-1])
    r = scan_instrument(client, "X_USDT", "15m", "4h", swing_k=2)
    assert r.trend == "downtrend"
    assert r.actionable is False
    assert r.score <= 20


def test_uptrend_pocket_candle_actionable():
    # exec: impulse up then pullback hammer into golden pocket (like strategy test)
    exec_closes = [102, 100, 103, 101, 99, 101, 100, 96, 104, 110, 116, 120, 114, 108]
    ex = [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1) for i, c in enumerate(exec_closes)]
    ex.append(Candle(t=99, o=103.0, h=103.3, l=99.0, c=103.2, v=1))  # hammer in pocket

    class C:
        def get_quote(self, inst): return Quote(inst, bid=103.2, ask=103.2, last=103.2)
        def get_candles(self, inst, tf):
            return [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1) for i, c in enumerate(UP)] if tf == "4h" else ex
    r = scan_instrument(C(), "BTC_USDT", "15m", "4h", swing_k=2)
    assert r.trend == "uptrend"
    assert r.in_pocket is True
    assert r.candle != ""
    assert r.actionable is True
    assert r.stop is not None and r.stop < r.entry
    assert r.tp2 > r.tp1 > r.entry
    assert r.score >= 75


def test_scan_market_ranks_and_handles_errors():
    class C:
        def get_quote(self, inst):
            if inst == "BAD_USDT":
                raise RuntimeError("no data")
            return Quote(inst, bid=DOWN[-1], ask=DOWN[-1], last=DOWN[-1])
        def get_candles(self, inst, tf):
            return [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1) for i, c in enumerate(DOWN)]
    rows = scan_market(C(), ["A_USDT", "BAD_USDT", "B_USDT"], "15m", "4h", swing_k=2)
    assert len(rows) == 3
    # errored row sorts last
    assert rows[-1].instrument == "BAD_USDT" and rows[-1].error
