"""Configuration loading: merges config.yaml + environment (.env)."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # dotenv is optional at runtime
    pass


@dataclass
class EngineConfig:
    instruments: list[str]
    timeframe: str               # execution timeframe (entries)
    poll_interval_seconds: int
    quote_currency: str
    trend_timeframe: str | None = None   # higher timeframe for top-down direction


@dataclass
class StrategyConfig:
    name: str
    params: dict[str, Any]


@dataclass
class RiskConfig:
    starting_capital: float
    risk_per_trade: float
    max_position_fraction: float
    stop_loss_pct: float
    take_profit_pct: float
    max_daily_loss_pct: float
    max_open_positions: int
    # Reward-to-risk multiple (the guide: minimum 1, prefer 2–3). Take-profit
    # distance = rr_ratio * stop distance. Falls back to take_profit_pct only
    # when a trade has no explicit stop distance.
    rr_ratio: float = 2.0


@dataclass
class FeesConfig:
    taker_fee: float
    maker_fee: float
    slippage: float

    @property
    def round_trip_cost(self) -> float:
        """Total cost fraction to open + close a position (taker both sides)."""
        return 2 * (self.taker_fee + self.slippage)


@dataclass
class LoggingConfig:
    level: str
    trades_csv: str


@dataclass
class Config:
    mode: str  # "paper" or "live"
    api_key: str
    api_secret: str
    api_base: str
    engine: EngineConfig
    strategy: StrategyConfig
    risk: RiskConfig
    fees: FeesConfig
    logging: LoggingConfig
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def is_live(self) -> bool:
        return self.mode.lower() == "live"


DEFAULT_API_BASE = "https://api.crypto.com/exchange/v1"


def load_config(path: str | Path = "config.yaml") -> Config:
    """Load configuration from YAML file and environment variables."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}

    mode = os.getenv("MODE", "paper").strip().lower()
    api_base = os.getenv("CRYPTOCOM_API_BASE", "").strip() or DEFAULT_API_BASE

    cfg = Config(
        mode=mode,
        api_key=os.getenv("CRYPTOCOM_API_KEY", "").strip(),
        api_secret=os.getenv("CRYPTOCOM_API_SECRET", "").strip(),
        api_base=api_base,
        engine=EngineConfig(**data["engine"]),
        strategy=StrategyConfig(**data["strategy"]),
        risk=RiskConfig(**data["risk"]),
        fees=FeesConfig(**data["fees"]),
        logging=LoggingConfig(**data["logging"]),
        raw=data,
    )

    if cfg.is_live and (not cfg.api_key or not cfg.api_secret):
        raise ValueError(
            "MODE=live requires CRYPTOCOM_API_KEY and CRYPTOCOM_API_SECRET in .env"
        )

    return cfg
