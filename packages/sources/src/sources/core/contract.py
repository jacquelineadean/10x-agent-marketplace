"""The files a gatherer writes to a run folder, and the checks that keep them honest.

`facts.json` groups facts under one top-level key per system, each record's `source`
being that system; `queries.json` names the query behind each fact; `digest.md` is what
Claude reads in place of both.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Any

from sources.core.systems import BY_ID

SCHEMA_VERSION = 1
LANES = ("mcp", "script")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MAX_QUERY = 2000


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def is_record(node: Any) -> bool:
    return isinstance(node, Mapping) and "value" in node


def facts_of(facts: Mapping[str, Any]) -> Iterator[tuple[str, Any]]:
    """Every fact by dotted path: records, bare values and series, outside `derive`."""

    def walk(node: Any, path: str) -> Iterator[tuple[str, Any]]:
        if isinstance(node, Mapping) and not is_record(node):
            for key, child in node.items():
                yield from walk(child, f"{path}.{key}")
        else:
            yield path, node

    for key, node in facts.items():
        if key != "derive":
            yield from walk(node, str(key))


def covering(path: str, entries: Mapping[str, Any]) -> str:
    """The queries entry for a fact: its own path or the nearest group above it, else ''."""
    parts = path.split(".")
    for end in range(len(parts), 0, -1):
        key = ".".join(parts[:end])
        if key in entries:
            return key
    return ""


def _date(value: Any) -> date | None:
    if isinstance(value, str) and DATE.match(value):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _entry(key: str, entry: Any, today: date, report: Report) -> None:
    where = f"queries.json {key}"
    if not isinstance(entry, Mapping):
        report.errors.append(f"{where}: must be an object")
        return
    system = str(entry.get("system", ""))
    if system != key.split(".")[0]:
        report.errors.append(f"{where}: system must be {key.split('.')[0]!r}, the fact's group")
    if entry.get("lane") not in LANES:
        report.errors.append(f"{where}: lane must be one of {', '.join(LANES)}")
    query = entry.get("query")
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY:
        report.errors.append(f"{where}: query must be the text of the query, 1 to 2000 chars")
    if not str(entry.get("connection", "")).strip():
        report.errors.append(f"{where}: connection must name the connector or connection")
    as_of = _date(entry.get("as_of"))
    if as_of is None or as_of > today:
        report.errors.append(f"{where}: as_of must be an ISO date no later than today")
    window = entry.get("window")
    if window is not None:
        start = _date(window.get("start")) if isinstance(window, Mapping) else None
        end = _date(window.get("end")) if isinstance(window, Mapping) else None
        if start is None or end is None or start > end:
            report.errors.append(f"{where}: window needs ISO start and end, start first")


def check(facts: Any, queries: Any, today: date) -> Report:
    """Problems that make a run folder unusable (errors) or untidy (warnings)."""
    report = Report()
    if not isinstance(facts, Mapping):
        report.errors.append("facts.json must hold a JSON object")
        return report
    entries = queries.get("queries") if isinstance(queries, Mapping) else None
    if not isinstance(entries, Mapping):
        report.errors.append("queries.json must hold {'schema_version': 1, 'queries': {...}}")
        return report
    for key in facts:
        if key != "derive" and key not in BY_ID:
            report.errors.append(
                f"facts.json key {key!r} is not a system; group facts under {', '.join(BY_ID)}"
            )
    paths = []
    for path, node in facts_of(facts):
        paths.append(path)
        group = path.split(".")[0]
        if is_record(node) and node.get("source") != group:
            report.errors.append(f"{path}: source must be {group!r}, the system it came from")
        if not covering(path, entries):
            report.errors.append(f"{path}: no entry in queries.json names its query")
    for key, entry in entries.items():
        _entry(str(key), entry, today, report)
        if not any(p == key or p.startswith(f"{key}.") for p in paths):
            report.warnings.append(f"queries.json {key}: names no fact in facts.json")
    return report
