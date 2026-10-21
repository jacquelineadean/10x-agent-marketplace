"""The `metrics.json` shape (schema_version 1). Each number in the digest and write-up is a key."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

from speedup.core import analysis
from speedup.core.model import BenchRun, Change, Point, Project
from speedup.core.records import History, points_of

SCHEMA_VERSION = 1


def build_metrics(
    project: Project,
    history: History,
    changes: list[Change],
    runs: list[BenchRun],
    generated_at: datetime,
    warnings: list[str] | None = None,
) -> dict[str, Any]:
    points: dict[str, list[Point]] = {j.id: points_of(history, j.id) for j in project.journeys}
    latest = analysis.latest_day(points)
    journeys = {
        j.id: analysis.analyze_journey(j, points[j.id], project, latest) for j in project.journeys
    }
    by_id = {j.id: j for j in project.journeys}
    ordered = sorted(changes, key=lambda c: (c.shipped is None, c.shipped, c.id))
    change_rows = [analysis.analyze_change(c, ordered, by_id, points, project) for c in ordered]
    benchmarks = {b.id: analysis.analyze_benchmark(b, runs) for b in project.benchmarks}
    windows = _windows(project, points, latest)
    unknown = sorted({j for c in changes for j in c.journeys if j not in by_id})
    notes = list(warnings or [])
    if unknown:
        notes.append(f"changes name journeys missing from the project: {', '.join(unknown)}")
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "project": project.name,
        "percentile": project.percentile,
        "as_of": latest.isoformat() if latest else None,
        "windows": windows,
        "headline": analysis.headline(journeys, change_rows, benchmarks),
        "journeys": journeys,
        "priorities": analysis.priorities(journeys),
        "changes": change_rows,
        "benchmarks": benchmarks,
        "rollout": analysis.rollout(change_rows),
        "limits": analysis.limits(journeys, project),
        "warnings": notes,
    }


def _windows(
    project: Project, points: dict[str, list[Point]], latest: date | None
) -> dict[str, Any]:
    longest = max(points.values(), key=len, default=[])
    windows = analysis.windows_for(project, longest, latest)
    if windows is None:
        return {}
    return {
        name: {"since": w.since.isoformat(), "until": w.until.isoformat(), "days": w.days}
        for name, w in (
            ("baseline", windows.baseline),
            ("current", windows.current),
            ("previous", windows.previous),
        )
        if w is not None
    }


def lookup(metrics: dict[str, Any], key: str) -> Any:
    """Resolve a dotted key such as `journeys.fresh-load.speedup` or `changes.c-0003.impact.0.p`."""
    node: Any = metrics
    for part in key.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        elif isinstance(node, list):
            node = next((item for item in node if _named(item, part)), None)
            if node is None:
                raise KeyError(key)
        else:
            raise KeyError(key)
    return node


def _named(item: Any, part: str) -> bool:
    return isinstance(item, dict) and part in (item.get("id"), item.get("journey"))
