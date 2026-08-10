"""Regression: one failing instrument must not abort the whole evaluation pass
(previously a single delisted/erroring symbol froze every price and STEPS=0)."""

import shutil
from pathlib import Path

from cryptoking.config import load_config
from cryptoking.engine import Engine
from cryptoking.exchange.cryptocom import Candle, Quote


def _flat_candles(n=40, price=100.0):
    return [Candle(t=i, o=price, h=price + 0.5, l=price - 0.5, c=price, v=1.0) for i in range(n)]


class _FakeClient:
    """Returns data for GOOD symbols; raises for BAD ones."""

    bad = {"BAD_USDT"}

    def get_quote(self, inst):
        if inst in self.bad:
            raise RuntimeError("instrument not found")
        return Quote(inst, bid=99.99, ask=100.01, last=100.0)

    def get_candles(self, inst, timeframe):
        if inst in self.bad:
            raise RuntimeError("instrument not found")
        return _flat_candles()


def _engine(tmp_path, instruments):
    cfg_dst = tmp_path / "config.yaml"
    shutil.copy(Path("config.yaml"), cfg_dst)
    config = load_config(cfg_dst)
    config.engine.instruments = instruments
    config.logging.trades_csv = str(tmp_path / "trades.csv")
    eng = Engine(config)
    eng.client = _FakeClient()  # no network
    return eng


def test_one_bad_symbol_does_not_freeze_the_pass(tmp_path):
    eng = _engine(tmp_path, ["BTC_USDT", "BAD_USDT", "ETH_USDT"])
    eng.step()

    # The pass completed despite the bad symbol.
    assert eng.steps == 1
    # Good symbols still got live prices.
    assert eng.last_prices["BTC_USDT"] == 100.0
    assert eng.last_prices["ETH_USDT"] == 100.0
    # The bad symbol has no price and is flagged, not crashing.
    assert "BAD_USDT" not in eng.last_prices
    assert "data unavailable" in eng.last_signals["BAD_USDT"]["reason"]
    assert eng.last_error and "BAD_USDT" in eng.last_error


def test_all_good_symbols_price_normally(tmp_path):
    eng = _engine(tmp_path, ["BTC_USDT", "ETH_USDT"])
    eng.step()
    assert eng.steps == 1
    assert set(eng.last_prices) == {"BTC_USDT", "ETH_USDT"}
    assert eng.last_error is None
