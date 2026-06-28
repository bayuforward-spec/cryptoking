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
class ExecutionConfig:
    # "market" = taker (crosses spread, taker fee); "limit" = maker (post inside
    # the spread, lower maker fee — far better for scalping/frequent trading).
    order_type: str = "market"
    # For limit orders: how far inside the spread to post, as a fraction of price.
    limit_offset: float = 0.0005


@dataclass
class AIConfig:
    # Use Claude to confirm/veto each BUY signal before entering.
    enabled: bool = False
    model: str = "claude-opus-4-8"
    # Reasoning effort for the API ("low"/"medium"/"high"); null = omit (works
    # on all models, including Haiku which rejects the effort param).
    effort: str | None = None
    # If the API is unavailable/errors: true = allow the trade, false = skip it.
    fail_open: bool = True


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
    execution: ExecutionConfig
    ai: AIConfig
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
        execution=ExecutionConfig(**(data.get("execution") or {})),
        ai=AIConfig(**(data.get("ai") or {})),
        logging=LoggingConfig(**data["logging"]),
        raw=data,
    )

    if cfg.is_live and (not cfg.api_key or not cfg.api_secret):
        raise ValueError(
            "MODE=live requires CRYPTOCOM_API_KEY and CRYPTOCOM_API_SECRET in .env"
        )

    return cfg


def to_yaml_dict(cfg: Config) -> dict[str, Any]:
    """Serialize the tunable parts of a Config back to a YAML-ready dict.

    Secrets and mode live in .env, never in the YAML file — they are omitted.
    """
    return {
        "engine": {
            "instruments": cfg.engine.instruments,
            "timeframe": cfg.engine.timeframe,
            "trend_timeframe": cfg.engine.trend_timeframe,
            "poll_interval_seconds": cfg.engine.poll_interval_seconds,
            "quote_currency": cfg.engine.quote_currency,
        },
        "strategy": {"name": cfg.strategy.name, "params": cfg.strategy.params},
        "risk": {
            "starting_capital": cfg.risk.starting_capital,
            "risk_per_trade": cfg.risk.risk_per_trade,
            "max_position_fraction": cfg.risk.max_position_fraction,
            "rr_ratio": cfg.risk.rr_ratio,
            "stop_loss_pct": cfg.risk.stop_loss_pct,
            "take_profit_pct": cfg.risk.take_profit_pct,
            "max_daily_loss_pct": cfg.risk.max_daily_loss_pct,
            "max_open_positions": cfg.risk.max_open_positions,
        },
        "execution": {
            "order_type": cfg.execution.order_type,
            "limit_offset": cfg.execution.limit_offset,
        },
        "ai": {
            "enabled": cfg.ai.enabled,
            "model": cfg.ai.model,
            "effort": cfg.ai.effort,
            "fail_open": cfg.ai.fail_open,
        },
        "fees": {
            "taker_fee": cfg.fees.taker_fee,
            "maker_fee": cfg.fees.maker_fee,
            "slippage": cfg.fees.slippage,
        },
        "logging": {"level": cfg.logging.level, "trades_csv": cfg.logging.trades_csv},
    }


def save_config(cfg: Config, path: str | Path = "config.yaml") -> None:
    with Path(path).open("w", encoding="utf-8") as fh:
        yaml.safe_dump(to_yaml_dict(cfg), fh, sort_keys=False, default_flow_style=False)
