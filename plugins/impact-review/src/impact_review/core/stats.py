"""Small statistics helpers shared by the metric rules."""

from __future__ import annotations

import math
from collections.abc import Sequence


def median(values: Sequence[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2:
        return float(ordered[middle])
    return (ordered[middle - 1] + ordered[middle]) / 2


def percentile(values: Sequence[float], share: float) -> float | None:
    """Nearest-rank percentile; `share` is between 0 and 1."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, math.ceil(share * len(ordered)))
    return float(ordered[rank - 1])


def rounded(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value, digits)


def ratio(numerator: int, denominator: int, digits: int = 2) -> float:
    return round(numerator / denominator, digits) if denominator else 0.0
