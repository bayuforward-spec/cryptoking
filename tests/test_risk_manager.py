from cryptoking.config import RiskConfig
from cryptoking.execution.broker import Position
from cryptoking.risk.risk_manager import RiskManager


def make_risk(**over):
    base = dict(
        starting_capital=1000.0,
        risk_per_trade=0.01,
        max_position_fraction=0.25,
        stop_loss_pct=0.004,
        take_profit_pct=0.008,
        max_daily_loss_pct=0.05,
        max_open_positions=2,
    )
    base.update(over)
    return RiskManager(RiskConfig(**base))


def test_size_entry_respects_risk_per_trade():
    rm = make_risk()
    d = rm.size_entry(equity=1000.0, price=100.0, num_open_positions=0)
    assert d.allowed
    # risk_capital = 10; stop 0.004 -> notional 2500, capped at 25% of 1000 = 250
    assert d.quote_amount == 250.0


def test_max_open_positions_blocks():
    rm = make_risk()
    d = rm.size_entry(1000.0, 100.0, num_open_positions=2)
    assert not d.allowed


def test_daily_loss_kill_switch():
    rm = make_risk()
    rm.start_day(1000.0)
    rm.update_equity(940.0)  # -6% > 5% limit
    assert rm.halted
    d = rm.size_entry(940.0, 100.0, 0)
    assert not d.allowed


def test_stop_and_target_triggers():
    rm = make_risk()
    pos = Position("BTC_USDT", quantity=1.0, entry_price=100.0)
    assert rm.exit_for_stop_or_target(pos, 99.5) == "stop_loss"
    assert rm.exit_for_stop_or_target(pos, 100.9) == "take_profit"
    assert rm.exit_for_stop_or_target(pos, 100.1) is None
