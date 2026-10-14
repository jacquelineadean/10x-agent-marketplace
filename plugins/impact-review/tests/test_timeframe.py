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
