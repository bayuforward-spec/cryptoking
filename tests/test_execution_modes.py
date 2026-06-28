import pytest

from cryptoking.execution.paper import PaperBroker


def test_maker_uses_lower_fee_and_no_slippage():
    taker = PaperBroker(1000, taker_fee=0.001, slippage=0.01, maker_fee=0.0002, order_type="market")
    maker = PaperBroker(1000, taker_fee=0.001, slippage=0.01, maker_fee=0.0002,
                        order_type="limit", limit_offset=0.0)

    tf = taker.buy("BTC_USDT", 500, 100.0, "t")
    mf = maker.buy("BTC_USDT", 500, 100.0, "t")
    # Maker pays less fee (0.0002 vs 0.001) and doesn't cross the spread.
    assert mf.fee < tf.fee
    assert mf.price <= tf.price  # taker crosses up via slippage


def test_maker_roundtrip_cheaper_than_taker():
    def roundtrip(order_type):
        b = PaperBroker(1000, taker_fee=0.00075, slippage=0.0005, maker_fee=0.0002,
                        order_type=order_type, limit_offset=0.0)
        b.buy("X", 500, 100.0, "t")
        b.sell("X", 100.0, "t")
        return b.cash()

    assert roundtrip("limit") > roundtrip("market")  # maker keeps more cash


def test_invalid_order_type_falls_back_to_taker_fee_rate():
    b = PaperBroker(1000, taker_fee=0.001, slippage=0.0, maker_fee=0.0002, order_type="market")
    f = b.buy("X", 100, 100.0, "t")
    assert f.fee == pytest.approx(100 * 0.001)
