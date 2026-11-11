"""Windows and periods: the calendar slices a collector counts in, and a refresh's window.

A window's `start` and `end` are inclusive ISO dates, as `queries.json` writes them. A
period series labels days and weeks by their first date (weeks start on Monday), months
`2026-07`, quarters `2026-Q3` and years `2026`; the first and last periods are cut to the
window.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

PERS = ("day", "week", "month", "quarter", "year")
# Each period costs one request for a counting collector; 120 covers a daily season.
MAX_PERIODS = 120


class PeriodError(ValueError):
    """A window or period a collector cannot read, with what to change."""


@dataclass(frozen=True)
class Window:
    start: date
    end: date

    @property
    def until(self) -> date:
        """The day after the window, for queries that take an exclusive bound."""
        return self.end + timedelta(days=1)

    def as_json(self) -> dict[str, str]:
        return {"start": self.start.isoformat(), "end": self.end.isoformat()}

    def text(self) -> str:
        return f"{self.start.isoformat()}..{self.end.isoformat()}"


@dataclass(frozen=True)
class Period:
    label: str
    window: Window


def window(raw: Any) -> Window:
    """A window from `{"start": ISO date, "end": ISO date}`, start first."""
    if not isinstance(raw, Mapping):
        raise PeriodError("window must be {'start': 'YYYY-MM-DD', 'end': 'YYYY-MM-DD'}")
    try:
        start, end = date.fromisoformat(str(raw["start"])), date.fromisoformat(str(raw["end"]))
    except (KeyError, ValueError) as exc:
        raise PeriodError("window needs ISO dates for start and end") from exc
    if start > end:
        raise PeriodError("window start comes after its end")
    return Window(start, end)


def first_day(per: str, day: date) -> date:
    """The first date of the period that holds `day`."""
    if per == "day":
        return day
    if per == "week":
        return day - timedelta(days=day.weekday())
    if per == "month":
        return day.replace(day=1)
    if per == "quarter":
        return date(day.year, 3 * ((day.month - 1) // 3) + 1, 1)
    return date(day.year, 1, 1)


def next_first_day(per: str, day: date) -> date:
    """The first date of the period after the one that holds `day`."""
    start = first_day(per, day)
    if per == "day":
        return start + timedelta(days=1)
    if per == "week":
        return start + timedelta(days=7)
    months = {"month": 1, "quarter": 3, "year": 12}[per]
    total = start.year * 12 + start.month - 1 + months
    return date(total // 12, total % 12 + 1, 1)


def label(per: str, day: date) -> str:
    start = first_day(per, day)
    if per in ("day", "week"):
        return start.isoformat()
    if per == "month":
        return f"{start.year}-{start.month:02d}"
    if per == "quarter":
        return f"{start.year}-Q{(start.month - 1) // 3 + 1}"
    return str(start.year)


def periods(span: Window, per: str) -> list[Period]:
    """The periods of `per` that touch the window, cut to it."""
    if per not in PERS:
        raise PeriodError(f"per must be one of {', '.join(PERS)}")
    out: list[Period] = []
    day = span.start
    while day <= span.end:
        following = next_first_day(per, day)
        out.append(Period(label(per, day), Window(day, min(span.end, following - timedelta(1)))))
        if len(out) > MAX_PERIODS:
            raise PeriodError(
                f"{span.text()} holds more than {MAX_PERIODS} {per}s; use a longer period"
            )
        day = following
    return out


def _aligned(span: Window, per: str) -> bool:
    return first_day(per, span.start) == span.start and next_first_day(per, span.end) == (
        span.until
    )


def roll(span: Window, per: str | None, today: date) -> Window:
    """The window of the same length that ends with the last complete period before today.

    A window of whole periods (of `per`, or whole months when no period is named) keeps
    its count of periods; any other window keeps its count of days and ends yesterday. A
    window that already reaches that far stays as it is.
    """
    unit = per if per in PERS else "month"
    if unit != "day" and _aligned(span, unit):
        count = len(periods(span, unit))
        end = first_day(unit, today) - timedelta(days=1)
        start = first_day(unit, end)
        for _ in range(count - 1):
            start = first_day(unit, start - timedelta(days=1))
        rolled = Window(start, end)
    else:
        end = today - timedelta(days=1)
        rolled = Window(end - (span.end - span.start), end)
    return rolled if rolled.end > span.end else span
