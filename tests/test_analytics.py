import csv

from cryptoking.analytics import compute_stats


def write_ledger(path, pnls):
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["timestamp", "mode", "instrument", "side", "quantity",
                    "price", "fee", "reason", "realized_pnl", "equity"])
        for p in pnls:
            side = "SELL"
            w.writerow(["t", "paper", "BTC_USDT", side, "1", "100", "0", "x", p, "100"])


def test_expectancy_positive(tmp_path):
    # 40% win rate, wins of 30, losses of 10 -> EV = .4*30 - .6*10 = 6
    led = tmp_path / "trades.csv"
    write_ledger(led, [30, 30, 30, 30, -10, -10, -10, -10, -10, -10])
    s = compute_stats(str(led))
    assert s.closed_trades == 10
    assert s.wins == 4 and s.losses == 6
    assert abs(s.win_rate - 0.4) < 1e-9
    assert abs(s.expectancy - 6.0) < 1e-9
    assert abs(s.reward_risk - 3.0) < 1e-9
    assert s.profit_factor == 2.0  # 120 / 60


def test_empty_ledger(tmp_path):
    s = compute_stats(str(tmp_path / "nope.csv"))
    assert s.closed_trades == 0
    assert s.expectancy == 0.0
