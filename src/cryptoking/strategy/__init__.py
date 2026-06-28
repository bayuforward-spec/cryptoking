"""Trading strategies."""

from .base import Signal, Strategy
from .scalping import EmaRsiScalper
from .structure_fib import StructureFibStrategy

STRATEGIES = {
    "ema_rsi_scalper": EmaRsiScalper,
    "structure_fib": StructureFibStrategy,
}


def build_strategy(name: str, params: dict) -> Strategy:
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy '{name}'. Available: {list(STRATEGIES)}")
    return STRATEGIES[name](**params)


__all__ = [
    "Signal",
    "Strategy",
    "EmaRsiScalper",
    "StructureFibStrategy",
    "build_strategy",
    "STRATEGIES",
]
