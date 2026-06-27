from cryptoking.indicators import ema, rsi, sma


def test_sma_basic():
    assert sma([1, 2, 3, 4], 2) == 3.5
    assert sma([1, 2], 5) is None


def test_ema_trends_with_data():
    rising = list(range(1, 50))
    e = ema(rising, 10)
    assert e is not None
    # EMA of a rising series sits below the latest value but above the mean tail.
    assert e < rising[-1]


def test_rsi_all_gains_is_high():
    rising = [float(i) for i in range(1, 30)]
    r = rsi(rising, 14)
    assert r is not None
    assert r > 99  # monotonic increase -> RSI ~100


def test_rsi_all_losses_is_low():
    falling = [float(i) for i in range(30, 1, -1)]
    r = rsi(falling, 14)
    assert r is not None
    assert r < 1


def test_rsi_insufficient_data():
    assert rsi([1, 2, 3], 14) is None
