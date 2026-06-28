from cryptoking.backtest import Backtester, aggregate_candles
from cryptoking.config import FeesConfig, RiskConfig
from cryptoking.exchange.cryptocom import Candle
from cryptoking.strategy.structure_fib import StructureFibStrategy


def risk_cfg():
    return RiskConfig(
        starting_capital=200.0, risk_per_trade=0.01, max_position_fraction=0.25,
        stop_loss_pct=0.01, take_profit_pct=0.02, max_daily_loss_pct=0.05,
        max_open_positions=1, rr_ratio=2.0,
    )


def fees_cfg():
    return FeesConfig(taker_fee=0.00075, maker_fee=0.0004, slippage=0.0003)


def test_aggregate_candles():
    cs = [Candle(t=i, o=i, h=i + 2, l=i - 2, c=i + 1, v=1.0) for i in range(8)]
    agg = aggregate_candles(cs, 4)
    assert len(agg) == 2
    assert agg[0].o == cs[0].o
    assert agg[0].c == cs[3].c
    assert agg[0].h == max(c.h for c in cs[:4])
    assert agg[0].l == min(c.l for c in cs[:4])
    assert agg[0].v == 4.0


def test_backtest_runs_and_preserves_accounting():
    # flat-ish data: strategy likely won't trade, but the run must complete
    candles = [Candle(t=i, o=100, h=100.5, l=99.5, c=100, v=1.0) for i in range(200)]
    bt = Backtester(StructureFibStrategy(swing_k=2), risk_cfg(), fees_cfg(), trend_ratio=4)
    res = bt.run(candles)
    assert res.starting_equity == 200.0
    assert len(res.equity_curve) > 0
    # No trades on flat data -> equity unchanged.
    assert abs(res.final_equity - 200.0) < 1e-6
    assert res.stats.closed_trades == 0


def test_backtest_trends_produce_trades():
    # Layered sines create real impulses + pullbacks into the golden pocket.
    import math
    candles = []
    price = 100.0
    for i in range(1000):
        close = 100 + i * 0.03 + math.sin(i / 18) * 6 + math.sin(i / 4) * 1.0
        o = price
        h = max(o, close) + 0.6
        l = min(o, close) - 0.6
        candles.append(Candle(t=i, o=o, h=h, l=l, c=close, v=1.0))
        price = close
    strat = StructureFibStrategy(swing_k=2, require_candle_pattern=False)
    bt = Backtester(strat, risk_cfg(), fees_cfg(), trend_ratio=8)
    res = bt.run(candles)
    assert res.stats.closed_trades >= 1
