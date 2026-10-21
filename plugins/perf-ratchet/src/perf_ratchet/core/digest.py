"""The compact Markdown digest Claude reads. Hard cap 12,000 bytes, about 3,000 tokens.

Each number is followed by its `metrics.json` key in parentheses so the write-up can cite it.
"""

from __future__ import annotations

from typing import Any

from perf_ratchet.core.numbers import p_value, pct, speedup, with_unit

DIGEST_CAP_BYTES = 12_000
_TRIMMED = (
    "\n_Digest trimmed to fit the 12 KB cap; metrics.json and the dashboard hold the rest._\n"
)


def render_digest(metrics: dict[str, Any], max_changes: int = 40) -> str:
    """Keep the changes with the largest measured effects that fit, then cut with a note."""
    for limit in (max_changes, 30, 24, 20, 16, 12, 8, 4, 0):
        text = "\n".join(_sections(metrics, limit)) + "\n"
        if len(text.encode("utf-8")) <= DIGEST_CAP_BYTES:
            return text
    cut = text.encode("utf-8")[: DIGEST_CAP_BYTES - len(_TRIMMED.encode("utf-8"))]
    return cut.decode("utf-8", errors="ignore") + _TRIMMED


def _sections(metrics: dict[str, Any], change_limit: int) -> list[str]:
    return [
        *_header(metrics),
        *_headline(metrics),
        *_journeys(metrics),
        *_priorities(metrics),
        *_changes(metrics, change_limit),
        *_benchmarks(metrics),
        *_rollout(metrics),
        *_limits(metrics),
    ]


def _header(metrics: dict[str, Any]) -> list[str]:
    windows = metrics.get("windows") or {}
    lines = [
        f"# Performance digest: {metrics['project']}",
        "",
        f"Percentile {metrics['percentile']}. Data through {metrics['as_of'] or 'no data yet'}. "
        f"Generated {metrics['generated_at']}.",
    ]
    for name in ("baseline", "current", "previous"):
        if name in windows:
            w = windows[name]
            lines.append(
                f"- {name.capitalize()} window: {w['since']} to {w['until']} "
                f"({w['days']} days) (windows.{name})"
            )
    example = next(iter(metrics["journeys"]), "<journey>")
    lines += [
        f"Cite each number by its key in parentheses, for example (journeys.{example}.speedup).",
        "",
    ]
    return lines


def _headline(metrics: dict[str, Any]) -> list[str]:
    h = metrics["headline"]
    lines = ["## Headline"]
    if "geomean_speedup" in h:
        lines.append(
            f"- Geometric mean speedup across {h['journeys_measured']} journeys: "
            f"{speedup(h['geomean_speedup'])} (headline.geomean_speedup, "
            "headline.journeys_measured)"
        )
        lines.append(
            f"- Biggest win: {h['best_journey']} at {speedup(h['best_speedup'])} "
            "(headline.best_journey, headline.best_speedup)"
        )
    lines += [
        f"- Journeys at target: {h['journeys_at_target']} of {h['journeys_with_target']} "
        "(headline.journeys_at_target, headline.journeys_with_target)",
        f"- Journeys regressed this window: {h['journeys_regressed']} "
        f"(headline.journeys_regressed)",
        f"- Changes logged {h['changes']}, shipped {h['changes_shipped']}, at 100% "
        f"{h['changes_at_full_rollout']}, rolled back {h['changes_rolled_back']}, with a "
        f"measured improvement {h['changes_improved']} (headline.changes, "
        f"headline.changes_shipped, "
        "headline.changes_at_full_rollout, headline.changes_rolled_back, "
        "headline.changes_improved)",
        f"- Feature flags added {h['flags_added']}, removed {h['flags_removed']}, still open "
        f"{h['flags_open']} (headline.flags_added, headline.flags_removed, headline.flags_open)",
        f"- Guardrail benchmarks {h['guardrails']}, with a ceiling {h['guardrails_with_ceiling']} "
        "(headline.guardrails, headline.guardrails_with_ceiling)",
    ]
    if "median_ceiling_reduction_pct" in h:
        lines.append(
            f"- Median ceiling cut since the first run: "
            f"{pct(h['median_ceiling_reduction_pct'], False)}"
            " (headline.median_ceiling_reduction_pct)"
        )
    return [*lines, ""]


def _journeys(metrics: dict[str, Any]) -> list[str]:
    lines = [
        "## Journeys",
        "| Journey | Status | Baseline | Current | Speedup | vs baseline | Target | Gap | Key |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for journey_id, j in metrics["journeys"].items():
        unit = j["unit"]
        lines.append(
            f"| {j['name']} | {j['status']} | {with_unit(j.get('baseline'), unit)} | "
            f"{with_unit(j.get('current'), unit)} | {speedup(j.get('speedup'))} | "
            f"{pct(j.get('improvement_pct'))} (p {p_value(j.get('vs_baseline_p'))}) | "
            f"{with_unit(j.get('target'), unit)} | {pct(j.get('gap_to_target_pct'), False)} | "
            f"journeys.{journey_id}.* |"
        )
    regressed = [(k, j) for k, j in metrics["journeys"].items() if j.get("regressed")]
    for journey_id, j in regressed:
        lines.append(
            f"- REGRESSION {journey_id}: {pct(j['vs_previous_pct'])} vs previous window, "
            f"p {p_value(j['vs_previous_p'])} (journeys.{journey_id}.vs_previous_pct, "
            f"journeys.{journey_id}.vs_previous_p)"
        )
    lines.append(
        "Sources: " + "; ".join(f"{k}: {j['source']}" for k, j in metrics["journeys"].items())
    )
    return [*lines, ""]


def _priorities(metrics: dict[str, Any]) -> list[str]:
    rows = metrics["priorities"]
    if not rows:
        return ["## Where to look next", "- Every journey with a target meets it.", ""]
    lines = ["## Where to look next (weighted gap to target, regressions first)"]
    for index, row in enumerate(rows[:8]):
        lines.append(
            f"{index + 1}. {row['journey']}: {pct(row['gap_to_target_pct'], False)} over target, "
            f"weight {row['weight']:g}, score {row['score']:g}, {row['status']} "
            f"(priorities.{index}.gap_to_target_pct)"
        )
    return [*lines, ""]


def _changes(metrics: dict[str, Any], limit: int) -> list[str]:
    changes = metrics["changes"]
    if not changes:
        return ["## Changes", "- None logged yet.", ""]
    kept = {c["id"] for c in sorted(changes, key=_effect, reverse=True)[:limit]}
    shown = [c for c in changes if c["id"] in kept]
    note = "" if len(shown) == len(changes) else ", largest measured effects kept"
    lines = [f"## Changes ({len(shown)} of {len(changes)}{note})"]
    for change in shown:
        key = f"changes.{change['id']}"
        flag = f", flag {change['flag']}" + (" removed" if change["flag_removed"] else "")
        lines.append(
            f"- {change['id']} {change['shipped'] or 'unshipped'} "
            f"[{change['stage']}{flag if change['flag'] else ''}] "
            f"{change['title']}"
        )
        for row in change["impact"]:
            if "improvement_pct" in row:
                lines.append(
                    f"  - {row['journey']}: {with_unit(row['before'], row['unit'])} -> "
                    f"{with_unit(row['after'], row['unit'])}, {pct(row['improvement_pct'])}, "
                    f"{speedup(row['speedup'])}, p {p_value(row['p'])}, {row['verdict']} "
                    f"({key}.impact.{row['journey']}.*)"
                )
            else:
                lines.append(f"  - {row['journey']}: {row['verdict']}")
        if "proxy" in change:
            proxy = change["proxy"]
            lines.append(
                f"  - proxy {proxy['benchmark']}: {with_unit(proxy['before'], proxy['unit'])} -> "
                f"{with_unit(proxy['after'], proxy['unit'])}, "
                f"{pct(-proxy['reduction_pct'])} "
                f"({key}.proxy.*)"
            )
        if change["overlaps"]:
            lines.append(f"  - overlaps {', '.join(change['overlaps'])} on a shared journey")
        if change["notes"]:
            lines.append(f"  - notes: {change['notes']}")
    return [*lines, ""]


def _effect(change: dict[str, Any]) -> float:
    """Regressions first, then the largest field effect, then the proxy cut as a tiebreak."""
    if any(row.get("verdict") == "regressed" for row in change["impact"]):
        return float("inf")
    field = [abs(row["improvement_pct"]) for row in change["impact"] if "improvement_pct" in row]
    proxy = change.get("proxy", {}).get("reduction_pct", 0.0)
    return float(max(field, default=0.0) + proxy / 1000)


def _benchmarks(metrics: dict[str, Any]) -> list[str]:
    benchmarks = metrics["benchmarks"]
    if not benchmarks:
        return ["## Guardrails", "- No benchmarks yet.", ""]
    lines = ["## Guardrails (ceilings only move down)"]
    for bench_id, b in benchmarks.items():
        unit = b["unit"]
        state = (
            "within ceiling"
            if b.get("within_ceiling")
            else "OVER CEILING"
            if "within_ceiling" in b
            else "no run yet"
        )
        lines.append(
            f"- {bench_id} ({unit}): original {with_unit(b.get('original'), unit)}, ceiling "
            f"{with_unit(b.get('ceiling'), unit)} ({pct(b.get('ceiling_reduction_pct'), False)} "
            f"cut), latest {with_unit(b.get('latest'), unit)}, cv "
            f"{pct(b.get('latest_cv_pct'), False)}, "
            f"{state}{', NOISY' if b.get('noisy') else ''} "
            f"(benchmarks.{bench_id}.ceiling_reduction_pct)"
        )
    return [*lines, ""]


def _rollout(metrics: dict[str, Any]) -> list[str]:
    stages = metrics["rollout"]
    if not stages:
        return []
    body = ", ".join(f"{stage} {count}" for stage, count in stages.items())
    return ["## Rollout stages", f"- {body} (rollout)", ""]


def _limits(metrics: dict[str, Any]) -> list[str]:
    lines = ["## Limits of this data", *[f"- {note}" for note in metrics["limits"]]]
    lines += [f"- warning: {w}" for w in metrics["warnings"]]
    return lines
