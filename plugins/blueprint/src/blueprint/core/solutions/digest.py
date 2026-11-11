"""What Claude reads and cites from a simulation: the results as a facts file, so prose
takes each number through a token, and `digest.md`, capped at 12 KB.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from pathlib import PurePosixPath
from typing import Any

from chronicle_engine.core.story.facts import format_value

from blueprint.core.solutions.simulate import Results, Run, Swing, inputs_of

DIGEST_CAP = 12_000
SOURCE = "model"
FORMATS = ("int", "dec1", "dec2")
# The swings a digest lists for each approach and measure, largest first.
TOP_SWINGS = 2


def fact_key(path: str) -> str:
    """The top-level facts key for a solutions file: `solutions.json` gives `solutions`."""
    return PurePosixPath(path).stem.replace("-", "_")


def show(value: float, item: Mapping[str, Any]) -> str:
    """A value in its control's or measure's unit and decimals; halves round up, as on the page."""
    scale = 10 ** int(item["decimals"])
    rounded = math.floor(value * scale + 0.5) / scale
    return format_value(rounded, str(item["unit"]), FORMATS[int(item["decimals"])])


def control_text(control: Mapping[str, Any], value: float) -> str:
    """A control's value as a reader sees it: on or off, an option's label, or a number."""
    if control["kind"] == "toggle":
        return "on" if value else "off"
    if control["kind"] == "choice":
        return next(str(o["label"]) for o in control["options"] if o["value"] == value)
    return show(value, control)


def tidy(value: float) -> float:
    """Six significant digits: what a results file stores and a check compares."""
    return float(f"{value:.6g}")


def met(measure: Mapping[str, Any], value: float) -> bool | None:
    """Whether a value is inside the measure's budget; None when it has no budget."""
    if measure["budget"] is None:
        return None
    if measure["better"] == "higher":
        return bool(value >= measure["budget"])
    return bool(value <= measure["budget"])


def facts(run: Run) -> dict[str, Any]:
    """The results as facts: scenario, approach, measure, each with its unit and a note."""
    labels = {a["id"]: a["label"] for a in run.spec["approaches"]}
    scenes = {s["id"]: s["label"] for s in run.spec["scenarios"]}
    return {
        sid: {
            aid: {
                m["id"]: {
                    "value": tidy(values[m["id"]]),
                    "unit": m["unit"],
                    "source": SOURCE,
                    "note": f"{labels[aid]}, {scenes[sid]}, at the approach's own settings",
                }
                for m in run.spec["measures"]
            }
            for aid, values in by_approach.items()
        }
        for sid, by_approach in run.results.items()
    }


def stale(stored: Any, run: Run) -> bool:
    """Whether a stored results file differs from what the file computes now."""
    fresh = facts(run)
    if not isinstance(stored, Mapping) or set(stored) != set(fresh):
        return True
    for sid, by_approach in fresh.items():
        for aid, measures in by_approach.items():
            for mid, fact in measures.items():
                try:
                    if stored[sid][aid][mid]["value"] != fact["value"]:
                        return True
                except (KeyError, TypeError):
                    return True
    return False


def misses(spec: Mapping[str, Any], results: Results) -> list[str]:
    """One line per approach, scenario and measure outside its budget."""
    labels = {a["id"]: a["label"] for a in spec["approaches"]}
    lines = []
    for scenario in spec["scenarios"]:
        for aid, values in results[scenario["id"]].items():
            for m in spec["measures"]:
                if met(m, values[m["id"]]) is False:
                    lines.append(
                        f"- {labels.get(aid, aid)} misses {m['label']} in {scenario['label']}: "
                        f"{show(values[m['id']], m)} against {show(m['budget'], m)}."
                    )
    return lines


def table(
    spec: Mapping[str, Any],
    rows: Mapping[str, Mapping[str, float]],
    labels: Mapping[str, str] | None = None,
) -> list[str]:
    """A Markdown table of measures, one row per approach id, or per variant with `labels`."""
    labels = labels or {a["id"]: a["label"] for a in spec["approaches"]}
    head = "| Approach | " + " | ".join(m["label"] for m in spec["measures"]) + " |"
    lines = [head, "| --- |" + " --- |" * len(spec["measures"])]
    for rid, values in rows.items():
        cells = []
        for m in spec["measures"]:
            inside = met(m, values[m["id"]])
            mark = "" if inside is None else " (met)" if inside else " (missed)"
            cells.append(show(values[m["id"]], m) + mark)
        lines.append(f"| {labels.get(rid, rid)} (`{rid}`) | " + " | ".join(cells) + " |")
    return lines


def inputs_line(spec: Mapping[str, Any], values: Mapping[str, float]) -> str:
    return "; ".join(f"{c['label']} {show(values[c['id']], c)}" for c in spec["inputs"])


def assumptions(spec: Mapping[str, Any], values: Mapping[str, float]) -> list[str]:
    """Inputs with no source: the numbers a person must verify."""
    return [
        f"- {c['label']} (`{c['id']}`): {show(values[c['id']], c)}"
        + (f". {c['note']}" if c["note"] else "")
        for c in spec["inputs"]
        if not c["source"]
    ]


def _swing_lines(spec: Mapping[str, Any], swings: list[Swing]) -> list[str]:
    controls = {c["id"]: c for c in (*spec["inputs"], *spec["settings"])}
    measures = {m["id"]: m for m in spec["measures"]}
    lines = []
    for approach in spec["approaches"]:
        for mid, m in measures.items():
            mine = [s for s in swings if s.approach == approach["id"] and s.measure == mid]
            mine.sort(key=lambda s: abs(s.high - s.low), reverse=True)
            for s in mine[:TOP_SWINGS]:
                if s.low == s.high:
                    continue
                c = controls[s.control]
                ends = f"{control_text(c, c['min'])} to {control_text(c, c['max'])}"
                lines.append(
                    f"| {approach['id']} | {m['label']} | {c['label']} (`{c['id']}`) {ends} | "
                    f"{show(s.low, m)} | {show(s.high, m)} |"
                )
    return lines


def digest(run: Run, key: str) -> str:
    """digest.md: results by scenario, budget misses, the largest swings and assumptions."""
    spec = run.spec
    out = [
        f"# Solutions digest: {spec['title']}",
        "",
        f"Question: {spec['question']}",
        f"Model: {len(spec['approaches'])} approaches, {len(spec['inputs'])} inputs, "
        f"{len(spec['settings'])} settings, {len(spec['scenarios'])} scenarios, "
        f"{len(spec['measures'])} measures.",
        f"Fact tokens: `{{{{{key}.<scenario>.<approach>.<measure>}}}}`, source `{SOURCE}`.",
        "",
        "## Results at each approach's own settings",
    ]
    for scenario in spec["scenarios"]:
        given = inputs_line(spec, inputs_of(spec, scenario))
        out += ["", f"### {scenario['label']} (`{scenario['id']}`): {given}", ""]
        out += table(spec, run.results[scenario["id"]])
    missed = misses(spec, run.results)
    out += ["", "## Budgets missed", ""]
    out += missed or ["Every approach meets every budget in every scenario."]
    first = spec["scenarios"][0]["label"]
    out += ["", f"## Largest swings ({first}, one control moved alone)", ""]
    out += ["| Approach | Measure | Control, min to max | At min | At max |"]
    out += ["| --- | --- | --- | --- | --- |"]
    out += _swing_lines(spec, run.swings)
    guessed = assumptions(spec, inputs_of(spec, spec["scenarios"][0]))
    out += ["", "## Inputs with no source (assumptions to verify)", ""]
    out += guessed or ["Every input names a source."]
    text = "\n".join(out) + "\n"
    if len(text.encode("utf-8")) > DIGEST_CAP:
        cut = text.encode("utf-8")[: DIGEST_CAP - 80].decode("utf-8", "ignore")
        text = cut.rsplit("\n", 1)[0] + "\n\nCut at 12 KB: fewer scenarios or measures fit whole.\n"
    return text
