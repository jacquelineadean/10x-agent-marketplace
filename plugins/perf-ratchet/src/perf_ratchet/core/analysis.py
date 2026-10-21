"""Every number on the dashboard and in the write-up: journeys, change impact, guardrails.

Lower-is-better journeys (latency) and higher-is-better journeys (throughput) share one rule:
`speedup` above 1 and `improvement_pct` above 0 always mean better.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from perf_ratchet.core.model import Benchmark, BenchRun, Change, Journey, Point, Project, Window
from perf_ratchet.core.stats import geometric_mean, mann_whitney_p, median

SIGNIFICANCE = 0.05
MIN_POINTS = 3


@dataclass(frozen=True)
class Windows:
    baseline: Window | None
    current: Window
    previous: Window


def windows_for(project: Project, points: list[Point], as_of: date | None = None) -> Windows | None:
    """Current = the last `window_days` up to `as_of` (default the newest point); previous = the
    span before it. A default baseline starts at the first point and ends before the current
    window, so the two never share days; with too little history there is no baseline yet."""
    if not points:
        return None
    latest = as_of or points[-1].day
    span = timedelta(days=project.window_days - 1)
    current = Window(latest - span, latest)
    previous_until = current.since - timedelta(days=1)
    previous = Window(previous_until - span, previous_until)
    baseline = project.baseline
    if baseline is None:
        until = min(points[0].day + span, previous_until)
        baseline = Window(points[0].day, until) if until >= points[0].day else None
    return Windows(baseline, current, previous)


def values_in(points: list[Point], window: Window) -> list[float]:
    return [p.value for p in points if window.contains(p.day)]


def ratio(journey: Journey, before: float, after: float) -> float:
    """How many times better `after` is than `before` (above 1 is better)."""
    if before <= 0 or after <= 0:
        raise ValueError("values must be positive to compare")
    return before / after if journey.direction == "lower" else after / before


def improvement_pct(journey: Journey, before: float, after: float) -> float:
    change = (before - after) / before * 100
    return change if journey.direction == "lower" else -change


def analyze_journey(
    journey: Journey, points: list[Point], project: Project, as_of: date | None = None
) -> dict[str, Any]:
    """`as_of` is the newest day across all journeys, so a journey whose data stopped is stale."""
    windows = windows_for(project, points, as_of)
    result: dict[str, Any] = {
        "name": journey.name,
        "unit": journey.unit,
        "direction": journey.direction,
        "percentile": project.percentile,
        "target": journey.target,
        "weight": journey.weight,
        "source": _describe_source(journey),
        "days_with_data": len(points),
        "series": [[p.day.isoformat(), round(p.value, 3)] for p in points],
    }
    if windows is None:
        return {**result, "status": "no-data"}
    baseline_values = values_in(points, windows.baseline) if windows.baseline else []
    current_values = values_in(points, windows.current)
    previous_values = values_in(points, windows.previous)
    result["coverage_pct"] = round(len(current_values) / windows.current.days * 100, 1)
    baseline = median(baseline_values) if baseline_values else None
    current = median(current_values) if current_values else None
    previous = median(previous_values) if previous_values else None
    result.update(
        baseline=_round(baseline),
        current=_round(current),
        previous=_round(previous),
        best_day=_round(_best(journey, points)),
    )
    if baseline is not None and current is not None and baseline > 0 and current > 0:
        result["speedup"] = round(ratio(journey, baseline, current), 2)
        result["improvement_pct"] = round(improvement_pct(journey, baseline, current), 1)
        p_value = mann_whitney_p(baseline_values, current_values)
        result["vs_baseline_p"] = _round_p(p_value)
    if previous and current:
        result["vs_previous_pct"] = round(improvement_pct(journey, previous, current), 1)
        result["vs_previous_p"] = _round_p(mann_whitney_p(previous_values, current_values))
    if journey.target and current:
        gap = ratio(journey, current, journey.target) - 1
        result["gap_to_target_pct"] = round(max(gap, 0.0) * 100, 1)
        result["at_target"] = gap <= 0
    result["regressed"] = _regressed(result, project)
    result["status"] = _status(result)
    return result


def _regressed(result: dict[str, Any], project: Project) -> bool:
    change = result.get("vs_previous_pct")
    p_value = result.get("vs_previous_p")
    return (
        change is not None
        and change < -project.regression_threshold_pct
        and p_value is not None
        and p_value < SIGNIFICANCE
    )


def _status(result: dict[str, Any]) -> str:
    if result.get("current") is None:
        return "stale"
    if result["regressed"]:
        return "regressed"
    if result.get("at_target"):
        return "at-target"
    improvement = result.get("improvement_pct")
    if improvement is None:
        return "measuring"
    if improvement < 0:
        return "slower"
    return "improving" if improvement >= 1 else "flat"


def change_impact(
    change: Change, journeys: dict[str, Journey], history: dict[str, list[Point]], project: Project
) -> list[dict[str, Any]]:
    """Before/after daily values around the ship day, one row per journey the change names."""
    rows: list[dict[str, Any]] = []
    for journey_id in change.journeys:
        journey = journeys.get(journey_id)
        row: dict[str, Any] = {"journey": journey_id}
        if journey is None:
            rows.append({**row, "verdict": "unknown journey"})
            continue
        row["unit"] = journey.unit
        points = history.get(journey_id, [])
        if change.shipped is None:
            rows.append({**row, "verdict": "not shipped"})
            continue
        span = timedelta(days=project.impact_days)
        before_window = Window(change.shipped - span, change.shipped - timedelta(days=1))
        after_window = Window(change.shipped + timedelta(days=1), change.shipped + span)
        before = values_in(points, before_window)
        after = values_in(points, after_window)
        latest = points[-1].day if points else None
        if len(before) < MIN_POINTS or len(after) < MIN_POINTS:
            early = latest is not None and latest < after_window.until
            rows.append({**row, "verdict": "too early" if early else "not enough data"})
            continue
        before_value, after_value = median(before), median(after)
        if before_value <= 0 or after_value <= 0:
            rows.append({**row, "verdict": "not comparable (zero or negative values)"})
            continue
        p_value = mann_whitney_p(before, after)
        delta = improvement_pct(journey, before_value, after_value)
        row.update(
            before=_round(before_value),
            after=_round(after_value),
            improvement_pct=round(delta, 1),
            speedup=round(ratio(journey, before_value, after_value), 2),
            p=_round_p(p_value),
            days_before=len(before),
            days_after=len(after),
        )
        significant = p_value is not None and p_value < SIGNIFICANCE
        row["verdict"] = (
            "improved"
            if significant and delta > 0
            else "regressed"
            if significant and delta < 0
            else "no clear effect"
        )
        rows.append(row)
    return rows


def overlapping(change: Change, changes: list[Change], days: int) -> list[str]:
    """Other shipped changes on a shared journey within `days` of this one's ship day."""
    if change.shipped is None:
        return []
    shared = set(change.journeys)
    return [
        other.id
        for other in changes
        if other.id != change.id
        and other.shipped is not None
        and shared.intersection(other.journeys)
        and abs((other.shipped - change.shipped).days) <= days
    ]


def analyze_change(
    change: Change,
    changes: list[Change],
    journeys: dict[str, Journey],
    history: dict[str, list[Point]],
    project: Project,
) -> dict[str, Any]:
    units = {b.id: b.unit for b in project.benchmarks}
    result: dict[str, Any] = {
        "id": change.id,
        "title": change.title,
        "journeys": change.journeys,
        "shipped": change.shipped.isoformat() if change.shipped else None,
        "pr": change.pr,
        "flag": change.flag,
        "stage": change.stage,
        "flag_removed": change.flag_removed,
        "notes": change.notes,
        "impact": change_impact(change, journeys, history, project),
        "overlaps": overlapping(change, changes, project.impact_days),
    }
    if change.benchmark and change.proxy_before and change.proxy_after:
        result["proxy"] = {
            "benchmark": change.benchmark,
            "unit": units.get(change.benchmark, "instructions"),
            "before": change.proxy_before,
            "after": change.proxy_after,
            "reduction_pct": round((1 - change.proxy_after / change.proxy_before) * 100, 1),
        }
    return result


def analyze_benchmark(benchmark: Benchmark, runs: list[BenchRun]) -> dict[str, Any]:
    mine = sorted((r for r in runs if r.benchmark == benchmark.id), key=lambda r: r.day)
    latest = mine[-1] if mine else None
    original = benchmark.original or (mine[0].median if mine else None)
    result: dict[str, Any] = {
        "name": benchmark.name,
        "unit": benchmark.unit,
        "journeys": list(benchmark.journeys),
        "command": " ".join(benchmark.command),
        "original": original,
        "ceiling": benchmark.ceiling,
        "tolerance_pct": benchmark.tolerance_pct,
        "runs": len(mine),
        "history": [[r.day.isoformat(), r.median] for r in mine],
    }
    if original and benchmark.ceiling:
        result["ceiling_reduction_pct"] = round((1 - benchmark.ceiling / original) * 100, 1)
    if latest is not None:
        result["latest"] = latest.median
        result["latest_date"] = latest.day.isoformat()
        result["latest_cv_pct"] = round(latest.cv_pct, 2)
        result["noisy"] = latest.cv_pct > benchmark.max_cv_pct
        if original:
            result["latest_reduction_pct"] = round((1 - latest.median / original) * 100, 1)
        if benchmark.ceiling:
            limit = benchmark.ceiling * (1 + benchmark.tolerance_pct / 100)
            result["within_ceiling"] = latest.median <= limit
    return result


def priorities(journeys: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Journeys still short of target, worst weighted gap first: where to look next."""
    rows = [
        {
            "journey": journey_id,
            "gap_to_target_pct": data["gap_to_target_pct"],
            "weight": data["weight"],
            "score": round(data["gap_to_target_pct"] * data["weight"], 1),
            "status": data["status"],
        }
        for journey_id, data in journeys.items()
        if data.get("gap_to_target_pct")
    ]
    return sorted(rows, key=lambda r: (r["status"] != "regressed", -r["score"]))


def headline(
    journeys: dict[str, dict[str, Any]],
    changes: list[dict[str, Any]],
    benchmarks: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    speedups = {k: v["speedup"] for k, v in journeys.items() if v.get("speedup")}
    targeted = [v for v in journeys.values() if v.get("target") is not None]
    shipped = [c for c in changes if c["shipped"]]
    flagged = [c for c in changes if c["flag"]]
    reductions = [
        b["ceiling_reduction_pct"] for b in benchmarks.values() if "ceiling_reduction_pct" in b
    ]
    result: dict[str, Any] = {
        "journeys": len(journeys),
        "journeys_measured": len(speedups),
        "journeys_with_target": len(targeted),
        "journeys_at_target": sum(1 for v in targeted if v.get("at_target")),
        "journeys_regressed": sum(1 for v in journeys.values() if v.get("regressed")),
        "changes": len(changes),
        "changes_shipped": len(shipped),
        "changes_at_full_rollout": sum(1 for c in changes if c["stage"] == "100%"),
        "changes_rolled_back": sum(1 for c in changes if c["stage"] == "rolled-back"),
        "changes_improved": sum(
            1 for c in changes if any(i.get("verdict") == "improved" for i in c["impact"])
        ),
        "flags_added": len(flagged),
        "flags_removed": sum(1 for c in flagged if c["flag_removed"]),
        "flags_open": sum(1 for c in flagged if not c["flag_removed"]),
        "guardrails": len(benchmarks),
        "guardrails_with_ceiling": sum(1 for b in benchmarks.values() if b.get("ceiling")),
    }
    if speedups:
        result["geomean_speedup"] = round(geometric_mean(list(speedups.values())), 2)
        best = max(speedups, key=lambda k: speedups[k])
        result["best_journey"] = best
        result["best_speedup"] = speedups[best]
    if reductions:
        result["median_ceiling_reduction_pct"] = round(median(reductions), 1)
    return result


def rollout(changes: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for change in changes:
        counts[change["stage"]] = counts.get(change["stage"], 0) + 1
    return counts


def limits(journeys: dict[str, dict[str, Any]], project: Project) -> list[str]:
    notes = [
        f"Journey values are the median of daily {project.percentile} values over a "
        f"{project.window_days}-day window; a day's value is the median of that day's points.",
        f"Change impact compares {project.impact_days} days before and after the ship day with a "
        "Mann-Whitney rank test; overlapping changes on one journey share the effect.",
        "Field data moves with traffic mix, devices and releases outside this log.",
    ]
    for journey_id, data in journeys.items():
        coverage = data.get("coverage_pct")
        if coverage is not None and coverage < 70:
            notes.append(f"{journey_id}: only {coverage}% of current-window days have data.")
        if data.get("status") == "no-data":
            notes.append(f"{journey_id}: no data yet; run measure or import.")
    return notes


def _best(journey: Journey, points: list[Point]) -> float | None:
    if not points:
        return None
    values = [p.value for p in points]
    return min(values) if journey.direction == "lower" else max(values)


def _describe_source(journey: Journey) -> str:
    source = journey.source
    if source.kind == "datadog-rum":
        return f"Datadog RUM {source.aggregation}({source.measure}) where {source.query}"
    if source.kind == "file":
        return "imported file"
    return f"{source.kind}: {source.query}"


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3) if abs(value) < 10 else round(value, 1)


def _round_p(value: float | None) -> float | None:
    return None if value is None else round(value, 4)


def latest_day(history: dict[str, list[Point]]) -> date | None:
    days = [points[-1].day for points in history.values() if points]
    return max(days) if days else None
