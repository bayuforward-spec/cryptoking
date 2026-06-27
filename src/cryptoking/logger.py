"""Logging setup: console + rotating-ish file, plus a CSV trade ledger."""

from __future__ import annotations

import csv
import logging
import sys
from pathlib import Path

_TRADE_HEADER = [
    "timestamp",
    "mode",
    "instrument",
    "side",
    "quantity",
    "price",
    "fee",
    "reason",
    "realized_pnl",
    "equity",
]


def setup_logging(level: str = "INFO") -> logging.Logger:
    logger = logging.getLogger("cryptoking")
    if logger.handlers:  # already configured
        return logger

    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(sh)

    Path("logs").mkdir(exist_ok=True)
    fh = logging.FileHandler("logs/cryptoking.log", encoding="utf-8")
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger


class TradeLedger:
    """Append-only CSV record of every fill, for audit and analysis."""

    def __init__(self, path: str):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            with self.path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh).writerow(_TRADE_HEADER)

    def record(self, row: dict) -> None:
        with self.path.open("a", newline="", encoding="utf-8") as fh:
            csv.writer(fh).writerow([row.get(k, "") for k in _TRADE_HEADER])
