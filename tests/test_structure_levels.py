"""Tests for the KJO-method additions: Fibonacci extensions and horizontal
support/resistance level clustering."""

from cryptoking.exchange.cryptocom import Candle
from cryptoking.structure import (
    FIB_EXT_RATIOS,
    fib_extension,
    levels_relative_to,
    support_resistance,
)


def mk(closes):
    return [Candle(t=i, o=c, h=c + 0.5, l=c - 0.5, c=c, v=1.0) for i, c in enumerate(closes)]


def test_fib_extension_projects_above_high():
    ext = fib_extension(100.0, 200.0)  # span = 100
    # ratios are 1.272, 1.618, 2.0, 2.618 -> low + span*ratio
    assert ext == [227.2, 261.8, 300.0, 361.8]
    # every extension sits above the impulse high
    assert all(e > 200.0 for e in ext)
    assert len(ext) == len(FIB_EXT_RATIOS)


def test_fib_extension_ascending():
    ext = fib_extension(50.0, 60.0)
    assert ext == sorted(ext)


# Two clear price shelves: swings clustering around ~110 and ~130.
LEVELS = [100, 110, 100, 111, 101, 130, 120, 129, 121, 131, 119, 109, 100]


def test_support_resistance_clusters_swings():
    levels = support_resistance(mk(LEVELS), k=2, tol=0.02)
    assert levels, "expected at least one clustered level"
    # a level tested more than once should report touches > 1
    assert any(lv.touches >= 2 for lv in levels)


def test_levels_relative_to_tags_kind():
    levels = support_resistance(mk(LEVELS), k=2, tol=0.02)
    tagged = levels_relative_to(levels, price=115.0)
    assert all(lv.kind in ("support", "resistance") for lv in tagged)
    assert all(lv.price <= 115.0 for lv in tagged if lv.kind == "support")
    assert all(lv.price > 115.0 for lv in tagged if lv.kind == "resistance")


def test_support_resistance_empty_on_flat():
    # a monotonic ramp with no local extremes over a +/-2 window
    assert support_resistance(mk([1, 2, 3, 4, 5]), k=2) == []
