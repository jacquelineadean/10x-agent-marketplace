"""The decision a reader exports from the page, checked against the solutions file, and
`decision.md`: the approach and settings to implement, what the model expects of them in
every scenario, the checks that follow from the budgets and the assumptions to verify.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.model import Report

from blueprint.core.solutions import digest, simulate
from blueprint.core.solutions import spec as reader

LABEL_LENGTH = 80


def _clean(text: Any) -> str:
    """A label a reader typed, on one line and safe inside a Markdown table."""
    return " ".join(str(text).split()).replace("|", "/")[:LABEL_LENGTH]


def read(spec: Mapping[str, Any], raw: Any, report: Report) -> dict[str, Any] | None:
    """The checked decision, or None when it names what the solutions file lacks."""
    start = len(report.errors)
    if not isinstance(raw, Mapping):
        report.errors.append("decision: the file must hold a JSON object")
        return None
    approaches = {a["id"]: a for a in spec["approaches"]}
    inputs = {c["id"]: c for c in spec["inputs"]}
    variants = []
    for i, item in enumerate(v for v in raw.get("variants") or [] if isinstance(v, Mapping)):
        where = f"decision.variants[{i}]"
        approach = approaches.get(str(item.get("approach")))
        if approach is None:
            report.errors.append(f"{where}.approach {item.get('approach')!r} names no approach")
            continue
        own = {s["id"]: s for s in reader.settings_of(spec, approach["id"])}
        off = [str(name) for name in item.get("off") or []]
        for name in off:
            if name not in own or own[name]["off"] is None:
                report.errors.append(f"{where}.off {name!r} is not a setting that turns off")
        variants.append(
            {
                "id": str(item.get("id") or approach["id"]),
                "approach": approach["id"],
                "label": _clean(item.get("label") or approach["label"]),
                "settings": reader.values(item.get("settings"), own, f"{where}.settings", report),
                "off": off,
            }
        )
    chosen = next((v for v in variants if v["id"] == str(raw.get("chosen"))), None)
    if chosen is None:
        report.errors.append(f"decision.chosen {raw.get('chosen')!r} names no variant")
    added = [
        {
            "id": f"saved_{i + 1}",
            "label": _clean(item.get("label") or f"Saved scenario {i + 1}"),
            "text": "",
            "inputs": reader.values(
                item.get("inputs"), inputs, f"decision.scenarios[{i}].inputs", report
            ),
        }
        for i, item in enumerate(s for s in raw.get("scenarios") or [] if isinstance(s, Mapping))
    ]
    given = reader.values(raw.get("inputs"), inputs, "decision.inputs", report)
    if len(report.errors) > start:
        return None
    return {
        "chosen": chosen,
        "variants": variants,
        "inputs": given,
        "scenarios": [*spec["scenarios"], *added],
        "note": _clean(raw.get("note", "")),
    }


def _measures(
    spec: Mapping[str, Any], variant: Mapping[str, Any], scenario: Mapping[str, Any]
) -> dict[str, float]:
    approach = next(a for a in spec["approaches"] if a["id"] == variant["approach"])
    settings = simulate.settings_for(spec, approach, variant["settings"], frozenset(variant["off"]))
    return simulate.measure(approach, {**simulate.inputs_of(spec, scenario), **settings})


def _settings(spec: Mapping[str, Any], variant: Mapping[str, Any]) -> list[str]:
    approach = next(a for a in spec["approaches"] if a["id"] == variant["approach"])
    usual = simulate.settings_for(spec, approach)
    lines = ["| Setting | Decided | Default | Lands in |", "| --- | --- | --- | --- |"]
    for control in reader.settings_of(spec, approach["id"]):
        cid = control["id"]
        value = variant["settings"].get(cid, usual[cid])
        decided = digest.control_text(control, value)
        if cid in variant["off"]:
            decided = f"turned off ({digest.control_text(control, control['off'])})"
        changed = " (changed)" if cid in variant["off"] or value != usual[cid] else ""
        lands = f"`{control['key']}`" if control["key"] else "to locate"
        lines.append(
            f"| {control['label']} (`{cid}`) | {decided}{changed} | "
            f"{digest.control_text(control, usual[cid])} | {lands} |"
        )
    return lines if len(lines) > 2 else ["This approach has no settings."]


def _checks(spec: Mapping[str, Any], scenarios: list[Any], rows: Mapping[str, Any]) -> list[str]:
    """A check per budget under each scenario's inputs, then how many the model misses."""
    lines: list[str] = []
    missed = total = 0
    for scenario in scenarios:
        given = digest.inputs_line(spec, simulate.inputs_of(spec, scenario))
        lines.append(f"{scenario['label']}: {given}")
        for m in spec["measures"]:
            value = rows[scenario["id"]][m["id"]]
            inside = digest.met(m, value)
            if inside is None:
                continue
            total += 1
            missed += not inside
            bound = "at least" if m["better"] == "higher" else "at most"
            lines.append(
                f"- [ ] {m['label']} {bound} {digest.show(m['budget'], m)}. "
                f"The model gives {digest.show(value, m)}"
                + ("." if inside else ", outside the budget.")
            )
    if not total:
        return ["No measure has a budget, so the model sets no check."]
    if missed:
        lines += ["", f"The model puts {missed} of {total} checks outside their budget."]
    return lines


def brief(spec: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    """decision.md for the session that implements the chosen approach."""
    chosen = decision["chosen"]
    approach = next(a for a in spec["approaches"] if a["id"] == chosen["approach"])
    scenarios = list(decision["scenarios"])
    if decision["inputs"] and all(
        simulate.inputs_of(spec, s) != simulate.inputs_of(spec, {"inputs": decision["inputs"]})
        for s in scenarios
    ):
        scenarios.append(
            {"id": "decided", "label": "Inputs when decided", "inputs": decision["inputs"]}
        )
    rows = {s["id"]: _measures(spec, chosen, s) for s in scenarios}
    first = scenarios[0]
    out = [
        f"# Decision: {spec['title']}",
        "",
        f"Question: {spec['question']}",
        f"Chosen: **{chosen['label']}** (approach `{approach['id']}`). {approach['text']}".rstrip(),
    ]
    if decision["note"]:
        out += [f"Note from the page: {decision['note']}"]
    out += ["", "## Settings to implement", "", *_settings(spec, chosen)]
    out += ["", "## What the model expects of the choice", ""]
    labels = {s["id"]: s["label"] for s in scenarios}
    table = digest.table(spec, rows, labels)
    out += [table[0].replace("| Approach |", "| Scenario |", 1), *table[1:]]
    out += ["", "## Acceptance checks, one per budget and scenario", ""]
    out += _checks(spec, scenarios, rows)
    out += ["", f"## Compared in {first['label']}", ""]
    compared = digest.table(
        spec,
        {v["id"]: _measures(spec, v, first) for v in decision["variants"]},
        {v["id"]: v["label"] for v in decision["variants"]},
    )
    out += [compared[0].replace("| Approach |", "| Variant |", 1), *compared[1:]]
    guessed = digest.assumptions(spec, simulate.inputs_of(spec, first))
    out += ["", "## Assumptions to verify before relying on these numbers", ""]
    out += guessed or ["Every input names a source."]
    return "\n".join(out) + "\n"
