import pytest

from cryptoking.execution.paper import PaperBroker


def test_buy_then_sell_accounts_for_fees():
    b = PaperBroker(starting_cash=1000.0, taker_fee=0.00075, slippage=0.0)
    fill = b.buy("BTC_USDT", quote_amount=500.0, price=100.0, reason="t")
    # Spent 500: fee = 0.375, invested 499.625 at price 100 -> qty 4.99625
    assert fill.side == "BUY"
    assert b.cash() == pytest.approx(500.0)
    assert b.get_position("BTC_USDT").quantity == pytest.approx(499.625 / 100.0)

    sell = b.sell("BTC_USDT", price=100.0, reason="t")
    assert sell.side == "SELL"
    # Round trip at flat price must lose ~2x fee.
    assert b.cash() < 1000.0
    assert b.get_position("BTC_USDT") is None


def test_cannot_double_open():
    b = PaperBroker(1000.0, 0.0, 0.0)
    b.buy("BTC_USDT", 100.0, 100.0, "t")
    with pytest.raises(RuntimeError):
        b.buy("BTC_USDT", 100.0, 100.0, "t")


def test_equity_marks_to_market():
    b = PaperBroker(1000.0, 0.0, 0.0)
    b.buy("BTC_USDT", 500.0, 100.0, "t")
    # price doubles
    eq = b.equity({"BTC_USDT": 200.0})
    assert eq == pytest.approx(500.0 + 5.0 * 200.0)
