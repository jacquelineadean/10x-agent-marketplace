"""Turn source points into daily values, merge them into history, and (de)serialize records."""

from __future__ import annotations

import csv
import io
import json
import math
import re
from collections.abc import Iterable
from datetime import UTC, date, datetime
from typing import Any

from speedup.core.model import ROLLOUT_STAGES, BenchRun, Change, Point, Series
from speedup.core.stats import median

History = dict[str, dict[str, float]]
_CHANGE_ID = re.compile(r"^c-\d{4,}$")
_URL = re.compile(r"^https?://[^\s<>\"']+$")


def daily(stamped: Iterable[tuple[float, float]], scale: float = 1.0) -> tuple[Point, ...]:
    """(epoch seconds, value) pairs to one value per UTC day: the median of that day's points."""
    buckets: dict[date, list[float]] = {}
    for seconds, value in stamped:
        if value is None or not math.isfinite(value):  # NaN, +Inf and gaps carry no measurement
            continue
        day = datetime.fromtimestamp(seconds, tz=UTC).date()
        buckets.setdefault(day, []).append(float(value) * scale)
    return tuple(Point(day, median(values)) for day, values in sorted(buckets.items()))


def merge(history: History, series: Series) -> int:
    """Write the series into history; a newer fetch replaces a day. Returns days written."""
    days = history.setdefault(series.journey, {})
    for point in series.points:
        days[point.day.isoformat()] = round(point.value, 6)
    history[series.journey] = dict(sorted(days.items()))
    return len(series.points)


def points_of(history: History, journey: str) -> list[Point]:
    return [Point(date.fromisoformat(d), v) for d, v in sorted(history.get(journey, {}).items())]


def parse_import(text: str, filename: str, default_journey: str | None) -> list[Series]:
    """Read an import file: JSON (one series or a list) or CSV with date,value[,journey]."""
    if filename.lower().endswith(".csv"):
        return _parse_csv(text, filename, default_journey)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"{filename} is not valid JSON: {error}") from None
    items = data if isinstance(data, list) else [data]
    return [_parse_json_series(item, filename, default_journey) for item in items]


def _parse_json_series(item: Any, filename: str, default_journey: str | None) -> Series:
    if not isinstance(item, dict):
        raise ValueError(f"{filename}: each series must be an object")
    journey = str(item.get("journey") or default_journey or "")
    if not journey:
        raise ValueError(f"{filename}: series has no journey; pass --journey")
    scale = _number(item.get("scale", 1), filename)
    if scale <= 0:
        raise ValueError(f"{filename}: scale must be positive")
    points: list[Point] = []
    for raw in item.get("points") or []:
        if not isinstance(raw, dict) or "date" not in raw or "value" not in raw:
            raise ValueError(f"{filename}: points need date and value")
        value = _number(raw["value"], filename) * scale
        points.append(Point(_day(raw["date"], filename), value))
    samples = item.get("samples")
    if samples and not points:
        raise ValueError(f"{filename}: raw samples need a date; send daily points instead")
    source = str(item.get("source") or f"file {filename}")[:300]
    return Series(journey, tuple(sorted(points, key=lambda p: p.day)), source)


def _parse_csv(text: str, filename: str, default_journey: str | None) -> list[Series]:
    rows = list(csv.DictReader(io.StringIO(text)))
    if not rows or "date" not in rows[0] or "value" not in rows[0]:
        raise ValueError(f"{filename}: CSV needs a header with date,value (journey optional)")
    grouped: dict[str, list[Point]] = {}
    for row in rows:
        journey = (row.get("journey") or default_journey or "").strip()
        if not journey:
            raise ValueError(f"{filename}: row has no journey; add a journey column or --journey")
        point = Point(_day(row["date"], filename), _number(row["value"], filename))
        grouped.setdefault(journey, []).append(point)
    return [
        Series(j, tuple(sorted(p, key=lambda x: x.day)), f"file {filename}")
        for j, p in grouped.items()
    ]


def _day(value: Any, filename: str) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        raise ValueError(f"{filename}: '{value}' is not a YYYY-MM-DD date") from None


def _number(value: Any, filename: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{filename}: '{value}' is not a number") from None
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"{filename}: '{value}' is not a finite number")
    return number


def parse_bench_import(text: str, filename: str) -> list[BenchRun] | None:
    """Benchmark results exported by `bench` elsewhere: a JSON list of run records, else None."""
    if not filename.lower().endswith(".json"):
        return None
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(data, list)
        or not data
        or not all(isinstance(item, dict) and "benchmark" in item for item in data)
    ):
        return None
    try:
        return [bench_run_from(item) for item in data]
    except (KeyError, TypeError, ValueError) as error:
        raise ValueError(f"{filename}: benchmark record is malformed: {error}") from None


def change_from(raw: dict[str, Any]) -> Change:
    """Validate one change record from changes.jsonl."""
    change_id = str(raw.get("id", ""))
    if not _CHANGE_ID.match(change_id):
        raise ValueError(f"change id '{change_id}' must look like c-0001")
    title = str(raw.get("title", "")).strip()
    if not title or len(title) > 200:
        raise ValueError(f"{change_id}: title must be 1 to 200 characters")
    stage = str(raw.get("stage", "dev"))
    if stage not in ROLLOUT_STAGES:
        raise ValueError(f"{change_id}: stage '{stage}' must be one of {', '.join(ROLLOUT_STAGES)}")
    pr = str(raw.get("pr", ""))
    if pr and not _URL.match(pr):
        raise ValueError(f"{change_id}: pr must be an http(s) link")
    shipped = raw.get("shipped")
    known = {
        "id",
        "title",
        "journeys",
        "shipped",
        "pr",
        "flag",
        "stage",
        "flag_removed",
        "benchmark",
        "proxy_before",
        "proxy_after",
        "notes",
    }
    return Change(
        id=change_id,
        title=title,
        journeys=[str(j) for j in raw.get("journeys") or []],
        shipped=None if not shipped else date.fromisoformat(str(shipped)),
        pr=pr,
        flag=str(raw.get("flag", ""))[:100],
        stage=stage,
        flag_removed=bool(raw.get("flag_removed", False)),
        benchmark=str(raw.get("benchmark", "")),
        proxy_before=_optional(raw.get("proxy_before")),
        proxy_after=_optional(raw.get("proxy_after")),
        notes=str(raw.get("notes", ""))[:500],
        extra={k: v for k, v in raw.items() if k not in known},
    )


def change_to(change: Change) -> dict[str, Any]:
    record: dict[str, Any] = {
        "id": change.id,
        "title": change.title,
        "journeys": change.journeys,
        "shipped": change.shipped.isoformat() if change.shipped else None,
        "pr": change.pr,
        "flag": change.flag,
        "stage": change.stage,
        "flag_removed": change.flag_removed,
        "benchmark": change.benchmark,
        "proxy_before": change.proxy_before,
        "proxy_after": change.proxy_after,
        "notes": change.notes,
    }
    record.update(change.extra)
    return record


def next_change_id(changes: list[Change]) -> str:
    numbers = [int(c.id[2:]) for c in changes]
    return f"c-{(max(numbers) if numbers else 0) + 1:04d}"


def bench_run_to(run: BenchRun) -> dict[str, Any]:
    return {
        "benchmark": run.benchmark,
        "date": run.day.isoformat(),
        "values": list(run.values),
        "median": run.median,
        "cv_pct": round(run.cv_pct, 3),
        "commit": run.commit,
    }


def bench_run_from(raw: dict[str, Any]) -> BenchRun:
    return BenchRun(
        benchmark=str(raw["benchmark"]),
        day=date.fromisoformat(str(raw["date"])),
        values=tuple(float(v) for v in raw.get("values") or [raw["median"]]),
        median=float(raw["median"]),
        cv_pct=float(raw.get("cv_pct", 0.0)),
        commit=str(raw.get("commit", "")),
    )


def _optional(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)
