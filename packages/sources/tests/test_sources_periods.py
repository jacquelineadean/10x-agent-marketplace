"""Periods inside a window, their labels, and how a refresh moves a window."""

from __future__ import annotations

from datetime import date

import pytest
from sources.core.periods import PeriodError, Window, periods, roll, window


def _w(start: str, end: str) -> Window:
    return Window(date.fromisoformat(start), date.fromisoformat(end))


def test_months_quarters_and_years_carry_their_labels_and_are_cut_to_the_window() -> None:
    months = periods(_w("2026-07-15", "2026-09-30"), "month")
    assert [p.label for p in months] == ["2026-07", "2026-08", "2026-09"]
    assert months[0].window == _w("2026-07-15", "2026-07-31")
    assert [p.label for p in periods(_w("2026-01-01", "2026-12-31"), "quarter")] == [
        "2026-Q1",
        "2026-Q2",
        "2026-Q3",
        "2026-Q4",
    ]
    assert [p.label for p in periods(_w("2025-12-01", "2026-01-31"), "year")] == ["2025", "2026"]


def test_weeks_start_on_monday_and_days_are_iso_dates() -> None:
    weeks = periods(_w("2026-07-01", "2026-07-14"), "week")
    assert [p.label for p in weeks] == ["2026-06-29", "2026-07-06", "2026-07-13"]
    assert weeks[0].window == _w("2026-07-01", "2026-07-05")
    assert [p.label for p in periods(_w("2026-07-30", "2026-08-01"), "day")] == [
        "2026-07-30",
        "2026-07-31",
        "2026-08-01",
    ]


def test_too_many_periods_and_bad_windows_are_refused() -> None:
    with pytest.raises(PeriodError, match="more than 120 days"):
        periods(_w("2026-01-01", "2026-12-31"), "day")
    with pytest.raises(PeriodError, match="per must be"):
        periods(_w("2026-01-01", "2026-01-02"), "fortnight")
    with pytest.raises(PeriodError, match="start comes after"):
        window({"start": "2026-02-01", "end": "2026-01-01"})
    with pytest.raises(PeriodError, match="ISO dates"):
        window({"start": "July"})


def test_a_window_of_whole_months_rolls_to_the_last_complete_month() -> None:
    q3 = _w("2026-07-01", "2026-09-30")
    assert roll(q3, None, date(2026, 11, 1)) == _w("2026-08-01", "2026-10-31")
    assert roll(q3, "month", date(2027, 1, 15)) == _w("2026-10-01", "2026-12-31")
    assert roll(q3, None, date(2026, 10, 31)) == q3  # September is still the last full month


def test_other_windows_keep_their_days_and_end_yesterday() -> None:
    thirty = _w("2026-09-15", "2026-10-14")
    assert roll(thirty, None, date(2026, 11, 1)) == _w("2026-10-02", "2026-10-31")
    weeks = _w("2026-09-07", "2026-10-04")  # four whole weeks, Monday to Sunday
    assert roll(weeks, "week", date(2026, 10, 21)) == _w("2026-09-21", "2026-10-18")
