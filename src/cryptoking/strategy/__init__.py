"""Trading strategies."""

from .base import Signal, Strategy
from .scalping import EmaRsiScalper

STRATEGIES = {
    "ema_rsi_scalper": EmaRsiScalper,
}


def build_strategy(name: str, params: dict) -> Strategy:
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGIES)}")
    return STRATEGIES[name](**params)


__all__ = ["Signal", "Strategy", "EmaRsiScalper", "build_strategy", "STRATEGIES"]
