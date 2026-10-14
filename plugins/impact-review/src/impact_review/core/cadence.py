"""Consistency metrics from the daily contribution calendar."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from typing import Any

from impact_review.core.models import Timeframe

WEEKDAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


def longest_streak(active_days: set[date]) -> int:
    best = 0
    for day in active_days:
        if day - timedelta(days=1) in active_days:
            continue
        length, cursor = 1, day
        while cursor + timedelta(days=1) in active_days:
            cursor += timedelta(days=1)
            length += 1
        best = max(best, length)
    return best


def week_key(day: date) -> tuple[int, int]:
    iso = day.isocalendar()
    return iso.year, iso.week


def consistency_metrics(calendar: dict[date, int], timeframe: Timeframe) -> dict[str, Any]:
    inside = {
        day: count for day, count in calendar.items() if timeframe.since <= day <= timeframe.until
    }
    active = {day for day, count in inside.items() if count > 0}
    weeks_in_range = {
        week_key(timeframe.since + timedelta(days=offset)) for offset in range(timeframe.days)
    }
    active_weeks = {week_key(day) for day in active}
    by_weekday = Counter(
        WEEKDAYS[day.weekday()] for day, count in inside.items() for _ in range(count)
    )
    by_month: Counter[str] = Counter()
    for day, count in inside.items():
        by_month[day.strftime("%Y-%m")] += count
    return {
        "contributions": sum(inside.values()),
        "active_days": len(active),
        "days_in_timeframe": timeframe.days,
        "longest_streak_days": longest_streak(active),
        "active_weeks": len(active_weeks),
        "weeks_in_timeframe": len(weeks_in_range),
        "active_weeks_share": round(len(active_weeks) / len(weeks_in_range), 2)
        if weeks_in_range
        else 0.0,
        "by_weekday": {name: by_weekday.get(name, 0) for name in WEEKDAYS},
        "by_month": dict(sorted(by_month.items())),
    }
