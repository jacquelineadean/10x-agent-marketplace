"""Timeframe forms the user types, all resolved against `today` into an inclusive date range.

Named periods: `ytd` (default), `mtd`, `qtd`, `this year`, `this quarter`, `this month`,
`last year`, `last quarter`, `last month`, `last week` (previous whole calendar period),
`all` / `all time` (from the earliest account creation date in the scope).
Rolling windows ending today: `30d`, `last 30 days`, `2w`, `1m`, `past 3 months`, `6mo`,
`1q`, `1y`, `last 2 years`, `past year`.
Calendar periods: `2025`, `2026-Q3`, `2026-03`.
Ranges: `2026-01-01..2026-09-30`, or open-ended `2026-01-01..` (to today).
"""

from __future__ import annotations

import calendar
import re
from datetime import UTC, date, datetime, timedelta

from impact_review.core.models import Timeframe

MAX_CHUNK = timedelta(days=365)
GITHUB_LAUNCH = date(2008, 1, 1)

_UNITS = {
    "d": "day",
    "day": "day",
    "days": "day",
    "w": "week",
    "wk": "week",
    "wks": "week",
    "week": "week",
    "weeks": "week",
    "m": "month",
    "mo": "month",
    "mos": "month",
    "month": "month",
    "months": "month",
    "q": "quarter",
    "qtr": "quarter",
    "qtrs": "quarter",
    "quarter": "quarter",
    "quarters": "quarter",
    "y": "year",
    "yr": "year",
    "yrs": "year",
    "year": "year",
    "years": "year",
}
_ROLLING = re.compile(r"^(?:(?:last|past)\s+)?(\d+)\s*([a-z]+)$")
_PAST_ONE = re.compile(r"^past\s+([a-z]+)$")
_RANGE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})?$")
_YEAR = re.compile(r"^(\d{4})$")
_QUARTER = re.compile(r"^(\d{4})-?q([1-4])$")
_MONTH = re.compile(r"^(\d{4})-(\d{2})$")
_ALL = ("all", "all time", "all-time", "alltime", "lifetime")
FORMS_HINT = (
    "use ytd, mtd, qtd, last month, last quarter, last year, all time, 30d, 3m, 1y, "
    "2025, 2026-Q3, 2026-03, 2026-01-01..2026-09-30 or 2026-01-01.."
)


def add_months(day: date, months: int) -> date:
    """`day` moved by `months` calendar months, clamped to the target month's last day."""
    index = day.year * 12 + day.month - 1 + months
    year, month = divmod(index, 12)
    month += 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def _quarter_start(day: date) -> date:
    return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)


def _frame(since: date, until: date, label: str, today: date) -> Timeframe:
    """Clamp the end to today; a period that starts in the future is an error."""
    if since > today:
        raise ValueError(f"timeframe {label!r} starts after today ({today})")
    return Timeframe(since=since, until=min(until, today), label=label)


def _rolling(count: int, unit: str, today: date) -> Timeframe:
    if count < 1:
        raise ValueError("a rolling timeframe needs a count of at least 1")
    plural = unit if count == 1 else unit + "s"
    label = f"last {count} {plural}"
    if unit == "day":
        return Timeframe(today - timedelta(days=count - 1), today, label)
    if unit == "week":
        return Timeframe(today - timedelta(days=7 * count - 1), today, label)
    months = {"month": 1, "quarter": 3, "year": 12}[unit] * count
    return Timeframe(add_months(today, -months) + timedelta(days=1), today, label)


def _named(cleaned: str, today: date, earliest: date | None) -> Timeframe | None:
    if cleaned in ("", "ytd", "this year"):
        return Timeframe(date(today.year, 1, 1), today, "ytd")
    if cleaned in ("mtd", "this month"):
        return Timeframe(today.replace(day=1), today, "mtd")
    if cleaned in ("qtd", "this quarter"):
        return Timeframe(_quarter_start(today), today, "qtd")
    if cleaned in _ALL:
        since = min(earliest or GITHUB_LAUNCH, today)
        return Timeframe(since, today, "all time")
    if cleaned == "last year":
        year = today.year - 1
        return Timeframe(date(year, 1, 1), date(year, 12, 31), f"last year ({year})")
    if cleaned == "last quarter":
        start = add_months(_quarter_start(today), -3)
        end = _quarter_start(today) - timedelta(days=1)
        return Timeframe(start, end, f"last quarter ({start.year}-Q{(start.month + 2) // 3})")
    if cleaned == "last month":
        end = today.replace(day=1) - timedelta(days=1)
        return Timeframe(end.replace(day=1), end, f"last month ({end:%Y-%m})")
    if cleaned == "last week":
        monday = today - timedelta(days=today.weekday())
        return Timeframe(monday - timedelta(days=7), monday - timedelta(days=1), "last week")
    return None


def _calendar(cleaned: str, today: date) -> Timeframe | None:
    if match := _YEAR.match(cleaned):
        year = int(match.group(1))
        return _frame(date(year, 1, 1), date(year, 12, 31), str(year), today)
    if match := _QUARTER.match(cleaned):
        year, quarter = int(match.group(1)), int(match.group(2))
        start = date(year, 3 * quarter - 2, 1)
        end = add_months(start, 3) - timedelta(days=1)
        return _frame(start, end, f"{year}-Q{quarter}", today)
    if match := _MONTH.match(cleaned):
        year, month = int(match.group(1)), int(match.group(2))
        if not 1 <= month <= 12:
            raise ValueError(f"unknown month in timeframe {cleaned!r}")
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return _frame(start, end, f"{year}-{month:02d}", today)
    return None


def parse_timeframe(text: str, today: date, earliest: date | None = None) -> Timeframe:
    """Return the inclusive range for `text`; raise ValueError on an unknown form.

    `earliest` is the first day `all time` covers, normally the oldest account creation date
    among the people in scope; without it `all time` starts at GitHub's launch, 2008-01-01.
    """
    cleaned = " ".join(text.split()).lower()
    if (frame := _named(cleaned, today, earliest)) is not None:
        return frame
    if match := _ROLLING.match(cleaned):
        unit = _UNITS.get(match.group(2))
        if unit is None:
            raise ValueError(f"unknown unit in timeframe {text!r}; {FORMS_HINT}")
        return _rolling(int(match.group(1)), unit, today)
    if (match := _PAST_ONE.match(cleaned)) and (unit := _UNITS.get(match.group(1))):
        return _rolling(1, unit, today)
    if match := _RANGE.match(cleaned):
        since = date.fromisoformat(match.group(1))
        until = date.fromisoformat(match.group(2)) if match.group(2) else today
        if since > until:
            raise ValueError(f"timeframe start {since} is after end {until}")
        return Timeframe(since=since, until=until, label=f"{since}..{until}")
    if (frame := _calendar(cleaned, today)) is not None:
        return frame
    raise ValueError(f"unknown timeframe {text!r}; {FORMS_HINT}")


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
