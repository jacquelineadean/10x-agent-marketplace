"""Parse and validate `perf/speedup.json`, and write new ceilings back into its raw form."""

from __future__ import annotations

import copy
import re
from datetime import date
from typing import Any

from speedup.core.model import (
    PARSE_MODES,
    SOURCE_KINDS,
    Benchmark,
    Journey,
    Project,
    SourceQuery,
    Window,
)

SCHEMA_VERSION = 1
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
_PERCENTILE = re.compile(r"^(p50|p75|p90|p95|p99|median|avg)$")
_AGGREGATIONS = ("pc75", "pc90", "pc95", "pc99", "median", "avg", "max", "min")


class ProjectError(ValueError):
    """The project file is missing a field or has a wrong value; the message names it."""


def parse_project(raw: Any) -> Project:
    if not isinstance(raw, dict):
        raise ProjectError("project file must be a JSON object")
    version = raw.get("schema_version", SCHEMA_VERSION)
    if version != SCHEMA_VERSION:
        raise ProjectError(f"schema_version {version} is not supported (expected 1)")
    journeys = tuple(_journey(item, i) for i, item in enumerate(_list(raw, "journeys")))
    _unique([j.id for j in journeys], "journey")
    known = {j.id for j in journeys}
    benchmarks = tuple(
        _benchmark(item, i, known) for i, item in enumerate(_list(raw, "benchmarks"))
    )
    _unique([b.id for b in benchmarks], "benchmark")
    sources = raw.get("sources") or {}
    if not isinstance(sources, dict):
        raise ProjectError("sources must be an object")
    percentile = str(raw.get("percentile", "p75"))
    if not _PERCENTILE.match(percentile):
        raise ProjectError(f"percentile '{percentile}' must be one of p50 p75 p90 p95 p99")
    return Project(
        name=_text(raw, "project", "project"),
        percentile=percentile,
        window_days=_int(raw, "window_days", 7, 1, 90),
        regression_threshold_pct=_float(raw, "regression_threshold_pct", 5.0, 0.0, 100.0),
        impact_days=_int(raw, "impact_days", 7, 2, 60),
        baseline=_window(raw.get("baseline"), "baseline"),
        datadog_site=str((sources.get("datadog") or {}).get("site", "")),
        prometheus_url=str((sources.get("prometheus") or {}).get("url", "")),
        journeys=journeys,
        benchmarks=benchmarks,
    )


def with_ceilings(raw: dict[str, Any], ceilings: dict[str, tuple[float, float]]) -> dict[str, Any]:
    """A copy of the raw project with `ceiling` and `original` set for the named benchmarks."""
    updated = copy.deepcopy(raw)
    for item in updated.get("benchmarks", []):
        if item.get("id") in ceilings:
            ceiling, original = ceilings[item["id"]]
            item["ceiling"] = ceiling
            item["original"] = original
    return updated


def _journey(item: Any, index: int) -> Journey:
    where = f"journeys[{index}]"
    if not isinstance(item, dict):
        raise ProjectError(f"{where} must be an object")
    journey_id = _id(item, where)
    source = item.get("source") or {"kind": "file"}
    if not isinstance(source, dict):
        raise ProjectError(f"{where}.source must be an object")
    kind = str(source.get("kind", ""))
    if kind not in SOURCE_KINDS:
        raise ProjectError(f"{where}.source.kind '{kind}' must be one of {', '.join(SOURCE_KINDS)}")
    query = str(source.get("query", ""))
    if kind != "file" and not query:
        raise ProjectError(f"{where}.source.query is required for {kind}")
    measure = str(source.get("measure", ""))
    if kind == "datadog-rum" and not measure.startswith("@"):
        raise ProjectError(
            f"{where}.source.measure must be a RUM attribute such as @view.loading_time"
        )
    aggregation = str(source.get("aggregation", "pc75"))
    if aggregation not in _AGGREGATIONS:
        raise ProjectError(f"{where}.source.aggregation must be one of {', '.join(_AGGREGATIONS)}")
    direction = str(item.get("direction", "lower"))
    if direction not in ("lower", "higher"):
        raise ProjectError(f"{where}.direction must be 'lower' or 'higher'")
    target = item.get("target")
    if target is not None and (not isinstance(target, int | float) or target <= 0):
        raise ProjectError(f"{where}.target must be a positive number")
    return Journey(
        id=journey_id,
        name=_text(item, "name", journey_id),
        unit=_text(item, "unit", "ms"),
        direction="lower" if direction == "lower" else "higher",
        target=None if target is None else float(target),
        weight=_float(item, "weight", 1.0, 0.0, 1000.0),
        source=SourceQuery(
            kind=kind,
            query=query,
            measure=measure,
            aggregation=aggregation,
            scale=_float(source, "scale", 1.0, 1e-12, 1e12),
        ),
    )


def _benchmark(item: Any, index: int, journeys: set[str]) -> Benchmark:
    where = f"benchmarks[{index}]"
    if not isinstance(item, dict):
        raise ProjectError(f"{where} must be an object")
    command = item.get("command")
    if (
        not isinstance(command, list)
        or not command
        or not all(isinstance(part, str) and part for part in command)
    ):
        raise ProjectError(f"{where}.command must be a non-empty list of strings (no shell)")
    parse = str(item.get("parse", "number"))
    if parse not in PARSE_MODES:
        raise ProjectError(f"{where}.parse must be one of {', '.join(PARSE_MODES)}")
    pattern = str(item.get("pattern", ""))
    if parse in ("json", "regex") and not pattern:
        raise ProjectError(f"{where}.pattern is required when parse is {parse}")
    if parse == "regex":
        try:
            compiled = re.compile(pattern)
        except re.error as error:
            raise ProjectError(f"{where}.pattern is not a valid regex: {error}") from None
        if compiled.groups < 1:
            raise ProjectError(f"{where}.pattern needs one capture group around the number")
    linked = tuple(str(j) for j in item.get("journeys") or [])
    unknown = [j for j in linked if j not in journeys]
    if unknown:
        raise ProjectError(f"{where}.journeys names unknown journeys: {', '.join(unknown)}")
    return Benchmark(
        id=_id(item, where),
        name=_text(item, "name", str(item.get("id"))),
        command=tuple(command),
        parse=parse,
        pattern=pattern,
        unit=_text(item, "unit", "instructions"),
        repeat=_int(item, "repeat", 3, 1, 50),
        journeys=linked,
        ceiling=_optional_positive(item, "ceiling", where),
        original=_optional_positive(item, "original", where),
        tolerance_pct=_float(item, "tolerance_pct", 1.0, 0.0, 50.0),
        headroom_pct=_float(item, "headroom_pct", 0.5, 0.0, 50.0),
        max_cv_pct=_float(item, "max_cv_pct", 2.0, 0.0, 100.0),
        timeout_s=_int(item, "timeout_s", 600, 1, 7200),
    )


def _window(value: Any, where: str) -> Window | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ProjectError(f"{where} must be an object with since and until")
    try:
        since = date.fromisoformat(str(value["since"]))
        until = date.fromisoformat(str(value["until"]))
    except (KeyError, ValueError):
        raise ProjectError(f"{where} needs since and until as YYYY-MM-DD") from None
    if until < since:
        raise ProjectError(f"{where}.until is before {where}.since")
    return Window(since, until)


def _list(raw: dict[str, Any], key: str) -> list[Any]:
    value = raw.get(key) or []
    if not isinstance(value, list):
        raise ProjectError(f"{key} must be a list")
    return value


def _id(item: dict[str, Any], where: str) -> str:
    value = str(item.get("id", ""))
    if not _ID.match(value):
        raise ProjectError(f"{where}.id '{value}' must be lowercase letters, digits and dashes")
    return value


def _text(raw: dict[str, Any], key: str, default: str) -> str:
    value = raw.get(key, default)
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise ProjectError(f"{key} must be text of 1 to 120 characters")
    return value.strip()


def _int(raw: dict[str, Any], key: str, default: int, low: int, high: int) -> int:
    value = raw.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool) or not low <= value <= high:
        raise ProjectError(f"{key} must be a whole number from {low} to {high}")
    return value


def _float(raw: dict[str, Any], key: str, default: float, low: float, high: float) -> float:
    value = raw.get(key, default)
    if not isinstance(value, int | float) or isinstance(value, bool) or not low <= value <= high:
        raise ProjectError(f"{key} must be a number from {low} to {high}")
    return float(value)


def _optional_positive(raw: dict[str, Any], key: str, where: str) -> float | None:
    value = raw.get(key)
    if value is None:
        return None
    if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
        raise ProjectError(f"{where}.{key} must be a positive number")
    return float(value)


def _unique(ids: list[str], kind: str) -> None:
    seen: set[str] = set()
    for item in ids:
        if item in seen:
            raise ProjectError(f"{kind} id '{item}' appears twice")
        seen.add(item)
