"""Timeframe forms the user types: `ytd`, `last 365d`, `2026-01-01..2026-09-30`."""

from __future__ import annotations

import re
from datetime import UTC, date, datetime, timedelta

from impact_review.core.models import Timeframe

MAX_CHUNK = timedelta(days=365)
_LAST_N = re.compile(r"^last\s+(\d+)\s*(d|days?)$", re.IGNORECASE)
_RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})$")


def parse_timeframe(text: str, today: date) -> Timeframe:
    """Return the inclusive range for `text`; raise ValueError on an unknown form."""
    cleaned = " ".join(text.split()).lower()
    if cleaned in ("", "ytd"):
        return Timeframe(since=date(today.year, 1, 1), until=today, label="ytd")
    if match := _LAST_N.match(cleaned):
        days = int(match.group(1))
        if days < 1:
            raise ValueError("last N days needs N of at least 1")
        return Timeframe(since=today - timedelta(days=days - 1), until=today, label=f"last {days}d")
    if match := _RANGE.match(cleaned):
        since, until = date.fromisoformat(match.group(1)), date.fromisoformat(match.group(2))
        if since > until:
            raise ValueError(f"timeframe start {since} is after end {until}")
        return Timeframe(since=since, until=until, label=f"{since}..{until}")
    raise ValueError(
        f"unknown timeframe {text!r}; use 'ytd', 'last 365d' or '2026-01-01..2026-09-30'"
    )


def start_of(day: date) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=UTC)


def end_of(day: date) -> datetime:
    return start_of(day) + timedelta(days=1) - timedelta(seconds=1)


def year_chunks(timeframe: Timeframe) -> list[tuple[datetime, datetime]]:
    """Split the range into pieces of at most one year, the contributionsCollection limit."""
    chunks: list[tuple[datetime, datetime]] = []
    start, end = start_of(timeframe.since), end_of(timeframe.until)
    while start <= end:
        stop = min(start + MAX_CHUNK - timedelta(seconds=1), end)
        chunks.append((start, stop))
        start = stop + timedelta(seconds=1)
    return chunks


def week_count(timeframe: Timeframe) -> float:
    return timeframe.days / 7
