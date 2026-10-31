from datetime import UTC, date, datetime

import pytest
from impact_review.core.models import Timeframe
from impact_review.core.timeframe import parse_timeframe, year_chunks

TODAY = date(2026, 10, 11)


def test_ytd_runs_from_january_first_to_today() -> None:
    frame = parse_timeframe("ytd", TODAY)
    assert (frame.since, frame.until, frame.label) == (date(2026, 1, 1), TODAY, "ytd")
    assert frame.days == 284


def test_empty_text_means_ytd() -> None:
    assert parse_timeframe("", TODAY) == parse_timeframe("ytd", TODAY)


@pytest.mark.parametrize("text", ["last 365d", "last 365 days", "LAST  365D"])
def test_last_n_days_is_inclusive_of_today(text: str) -> None:
    frame = parse_timeframe(text, TODAY)
    assert frame.days == 365
    assert frame.until == TODAY
    assert frame.since == date(2025, 10, 12)


def test_custom_range() -> None:
    frame = parse_timeframe("2026-01-01..2026-09-30", TODAY)
    assert (frame.since, frame.until) == (date(2026, 1, 1), date(2026, 9, 30))
    assert frame.label == "2026-01-01..2026-09-30"


@pytest.mark.parametrize("text", ["2026-09-30..2026-01-01", "last 0d", "yesterday", "2026-01-01"])
def test_bad_forms_raise(text: str) -> None:
    with pytest.raises(ValueError, match="timeframe|last N"):
        parse_timeframe(text, TODAY)


def test_year_chunks_split_ranges_longer_than_a_year() -> None:
    frame = Timeframe(date(2025, 6, 1), date(2026, 9, 30), "custom")
    chunks = year_chunks(frame)
    assert len(chunks) == 2
    first_start, first_stop = chunks[0]
    second_start, second_stop = chunks[1]
    assert first_start == datetime(2025, 6, 1, tzinfo=UTC)
    assert first_stop == datetime(2026, 5, 31, 23, 59, 59, tzinfo=UTC)
    assert second_start == datetime(2026, 6, 1, tzinfo=UTC)
    assert second_stop == datetime(2026, 9, 30, 23, 59, 59, tzinfo=UTC)
    assert all(stop - start < datetime(2027, 1, 1) - datetime(2026, 1, 1) for start, stop in chunks)


def test_year_chunks_single_chunk_for_a_short_range() -> None:
    assert len(year_chunks(Timeframe(date(2026, 1, 1), date(2026, 9, 30), "ytd"))) == 1


@pytest.mark.parametrize(
    ("text", "since", "until", "label"),
    [
        ("mtd", date(2026, 10, 1), TODAY, "mtd"),
        ("this month", date(2026, 10, 1), TODAY, "mtd"),
        ("qtd", date(2026, 10, 1), TODAY, "qtd"),
        ("this year", date(2026, 1, 1), TODAY, "ytd"),
        ("last month", date(2026, 9, 1), date(2026, 9, 30), "last month (2026-09)"),
        ("last quarter", date(2026, 7, 1), date(2026, 9, 30), "last quarter (2026-Q3)"),
        ("last year", date(2025, 1, 1), date(2025, 12, 31), "last year (2025)"),
        ("last week", date(2026, 9, 28), date(2026, 10, 4), "last week"),
        ("30d", date(2026, 9, 12), TODAY, "last 30 days"),
        ("2w", date(2026, 9, 28), TODAY, "last 2 weeks"),
        ("1m", date(2026, 9, 12), TODAY, "last 1 month"),
        ("past month", date(2026, 9, 12), TODAY, "last 1 month"),
        ("last 3 months", date(2026, 7, 12), TODAY, "last 3 months"),
        ("6mo", date(2026, 4, 12), TODAY, "last 6 months"),
        ("1q", date(2026, 7, 12), TODAY, "last 1 quarter"),
        ("1y", date(2025, 10, 12), TODAY, "last 1 year"),
        ("past year", date(2025, 10, 12), TODAY, "last 1 year"),
        ("last 2 years", date(2024, 10, 12), TODAY, "last 2 years"),
        ("2025", date(2025, 1, 1), date(2025, 12, 31), "2025"),
        ("2026", date(2026, 1, 1), TODAY, "2026"),
        ("2026-Q3", date(2026, 7, 1), date(2026, 9, 30), "2026-Q3"),
        ("2026q1", date(2026, 1, 1), date(2026, 3, 31), "2026-Q1"),
        ("2024-02", date(2024, 2, 1), date(2024, 2, 29), "2024-02"),
        ("2026-03-01..", date(2026, 3, 1), TODAY, "2026-03-01..2026-10-11"),
    ],
)
def test_named_rolling_and_calendar_forms(text: str, since: date, until: date, label: str) -> None:
    frame = parse_timeframe(text, TODAY)
    assert (frame.since, frame.until, frame.label) == (since, until, label)


def test_rolling_months_clamp_to_the_month_end() -> None:
    frame = parse_timeframe("1m", date(2026, 3, 31))
    assert frame.since == date(2026, 3, 1)


@pytest.mark.parametrize("text", ["all", "all time", "All-Time", "lifetime"])
def test_all_time_starts_at_the_earliest_account(text: str) -> None:
    frame = parse_timeframe(text, TODAY, earliest=date(2019, 4, 2))
    assert (frame.since, frame.until, frame.label) == (date(2019, 4, 2), TODAY, "all time")


def test_all_time_without_accounts_starts_at_github_launch() -> None:
    assert parse_timeframe("all time", TODAY).since == date(2008, 1, 1)


@pytest.mark.parametrize("text", ["2027", "2026-Q4x", "2026-13", "3 fortnights", "2027-01"])
def test_future_and_unknown_periods_raise(text: str) -> None:
    with pytest.raises(ValueError, match="timeframe|month"):
        parse_timeframe(text, TODAY)


def test_all_time_spans_many_year_chunks() -> None:
    frame = parse_timeframe("all time", TODAY, earliest=date(2019, 4, 2))
    assert len(year_chunks(frame)) == 8
