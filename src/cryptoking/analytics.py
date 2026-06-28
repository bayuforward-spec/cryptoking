"""Trade analytics — the math the guide insists on: win rate, R:R, expected
value, profit factor. Computed from the CSV trade ledger (closed SELL fills).
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Stats:
    closed_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0.0          # fraction in [0, 1]
    avg_win: float = 0.0
    avg_loss: float = 0.0          # positive number (magnitude)
    expectancy: float = 0.0        # expected value per trade (currency)
    profit_factor: float = 0.0     # gross profit / gross loss
    total_pnl: float = 0.0
    reward_risk: float = 0.0       # avg_win / avg_loss

    def as_dict(self) -> dict:
        return asdict(self)


def compute_stats(trades_csv: str) -> Stats:
    path = Path(trades_csv)
    if not path.exists():
        return Stats()

    pnls: list[float] = []
    with path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            # Only closed trades carry a realized PnL (SELL fills).
            if row.get("side") != "SELL":
                continue
            try:
                pnls.append(float(row.get("realized_pnl") or 0.0))
            except ValueError:
                continue

    if not pnls:
        return Stats()

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    n = len(pnls)
    gross_win = sum(wins)
    gross_loss = -sum(losses)  # positive magnitude

    avg_win = gross_win / len(wins) if wins else 0.0
    avg_loss = gross_loss / len(losses) if losses else 0.0
    win_rate = len(wins) / n
    loss_rate = len(losses) / n

    # Expected value per trade = winRate*avgWin - lossRate*avgLoss
    expectancy = win_rate * avg_win - loss_rate * avg_loss
    profit_factor = (gross_win / gross_loss) if gross_loss > 0 else float("inf") if gross_win > 0 else 0.0
    reward_risk = (avg_win / avg_loss) if avg_loss > 0 else 0.0

    return Stats(
        closed_trades=n,
        wins=len(wins),
        losses=len(losses),
        win_rate=win_rate,
        avg_win=avg_win,
        avg_loss=avg_loss,
        expectancy=expectancy,
        profit_factor=profit_factor,
        total_pnl=sum(pnls),
        reward_risk=reward_risk,
    )
