import math

import pytest
from speedup.core.stats import cv_pct, geometric_mean, mann_whitney_p, median, percentile


def test_percentile_interpolates_like_numpy_linear() -> None:
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile(values, 75) == pytest.approx(32.5)
    assert percentile(values, 0) == 10
    assert percentile(values, 100) == 40
    assert percentile([5.0], 75) == 5


def test_percentile_rejects_empty_and_out_of_range() -> None:
    with pytest.raises(ValueError):
        percentile([], 75)
    with pytest.raises(ValueError):
        percentile([1.0], 101)


def test_geometric_mean_treats_speedups_symmetrically() -> None:
    assert geometric_mean([3.0, 1 / 3]) == pytest.approx(1.0)
    assert geometric_mean([5.6, 1.7]) == pytest.approx(math.sqrt(5.6 * 1.7))
    with pytest.raises(ValueError):
        geometric_mean([1.0, 0.0])


def test_cv_is_zero_for_one_value_and_percent_otherwise() -> None:
    assert cv_pct([100.0]) == 0
    assert cv_pct([99.0, 100.0, 101.0]) == pytest.approx(1.0)


def test_rank_test_separates_clear_shifts_from_noise() -> None:
    before = [100.0, 102, 98, 101, 99, 103, 97]
    after = [60.0, 62, 58, 61, 59, 63, 57]
    p_shift = mann_whitney_p(before, after)
    p_same = mann_whitney_p(before, [101.0, 99, 100, 102, 98, 97, 103])
    assert p_shift is not None and p_shift < 0.01
    assert p_same is not None and p_same > 0.5


def test_rank_test_needs_three_values_each_and_handles_ties() -> None:
    assert mann_whitney_p([1.0, 2.0], [3.0, 4.0, 5.0]) is None
    assert mann_whitney_p([5.0] * 4, [5.0] * 4) == 1.0


def test_median_of_even_count() -> None:
    assert median([1.0, 3.0, 2.0, 4.0]) == 2.5
