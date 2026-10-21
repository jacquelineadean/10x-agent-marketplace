"""Small statistics with the standard library: percentiles, geometric mean, noise, rank test."""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


def percentile(values: Sequence[float], q: float) -> float:
    """Linear interpolation between closest ranks (the method numpy calls 'linear')."""
    if not values:
        raise ValueError("percentile of no values")
    if not 0 <= q <= 100:
        raise ValueError("q must be between 0 and 100")
    ordered = sorted(values)
    position = (len(ordered) - 1) * q / 100
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def median(values: Sequence[float]) -> float:
    if not values:
        raise ValueError("median of no values")
    return float(statistics.median(values))


def geometric_mean(ratios: Sequence[float]) -> float:
    """Geometric mean of positive ratios; the right average for speedups (3x and 1/3x cancel)."""
    if not ratios:
        raise ValueError("geometric mean of no values")
    if any(r <= 0 for r in ratios):
        raise ValueError("geometric mean needs positive values")
    return math.exp(sum(math.log(r) for r in ratios) / len(ratios))


def cv_pct(values: Sequence[float]) -> float:
    """Coefficient of variation in percent; 0 for a single value or a zero mean."""
    if len(values) < 2:
        return 0.0
    mean = statistics.fmean(values)
    if mean == 0:
        return 0.0
    return statistics.stdev(values) / abs(mean) * 100


def mann_whitney_p(before: Sequence[float], after: Sequence[float]) -> float | None:
    """Two-sided p-value of the Mann-Whitney U test, normal approximation with tie correction.

    Daily percentiles are not normally distributed and the windows are short, so a rank test
    is used instead of a t-test. Returns None when either side has fewer than 3 values.
    """
    n1, n2 = len(before), len(after)
    if n1 < 3 or n2 < 3:
        return None
    ranks = _ranks([*before, *after])
    r1 = sum(ranks[:n1])
    u1 = r1 - n1 * (n1 + 1) / 2
    mean_u = n1 * n2 / 2
    n = n1 + n2
    ties = _tie_term([*before, *after])
    variance = n1 * n2 / 12 * ((n + 1) - ties / (n * (n - 1)))
    if variance <= 0:
        return 1.0
    z = (abs(u1 - mean_u) - 0.5) / math.sqrt(variance)
    return min(1.0, math.erfc(max(z, 0.0) / math.sqrt(2)))


def _ranks(values: Sequence[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        average = (i + j) / 2 + 1
        for k in range(i, j + 1):
            ranks[order[k]] = average
        i = j + 1
    return ranks


def _tie_term(values: Sequence[float]) -> float:
    counts: dict[float, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return float(sum(t**3 - t for t in counts.values()))
