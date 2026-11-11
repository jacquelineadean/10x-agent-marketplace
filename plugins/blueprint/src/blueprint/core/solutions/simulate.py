"""The simulator: every approach's measures in every scenario, and how far each control
moves them.

A variant is an approach with its own setting values; a setting turned off takes its `off`
value. The page's script computes the same numbers from the same trees as a reader moves a
control, and compares its first answers with the ones computed here.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chronicle_engine.core.story.model import Report

from blueprint.core.solutions import formula
from blueprint.core.solutions import spec as reader

# Scenario id, then approach or variant id, then measure id.
Results = dict[str, dict[str, dict[str, float]]]


@dataclass(frozen=True)
class Swing:
    """One measure of one approach with one control at its lowest and its highest value."""

    control: str
    approach: str
    measure: str
    low: float
    high: float


@dataclass(frozen=True)
class Run:
    """A checked solutions file with what the simulator computed from it."""

    spec: dict[str, Any]
    results: Results
    swings: list[Swing]


def inputs_of(spec: Mapping[str, Any], scenario: Mapping[str, Any]) -> dict[str, float]:
    """Every input's value in a scenario: its own value unless the scenario sets one."""
    return {**{c["id"]: c["value"] for c in spec["inputs"]}, **scenario["inputs"]}


def settings_for(
    spec: Mapping[str, Any],
    approach: Mapping[str, Any],
    chosen: Mapping[str, float] | None = None,
    off: frozenset[str] = frozenset(),
) -> dict[str, float]:
    """A variant's setting values as the formulas read them."""
    out: dict[str, float] = {}
    for control in reader.settings_of(spec, approach["id"]):
        cid = control["id"]
        value = {**approach["settings"], **(chosen or {})}.get(cid, control["value"])
        out[cid] = control["off"] if cid in off and control["off"] is not None else value
    return out


def measure(approach: Mapping[str, Any], values: Mapping[str, float]) -> dict[str, float]:
    """An approach's measures for one set of input and setting values."""
    scope = dict(values)
    for name, tree in approach["steps"]:
        scope[name] = _named(name, tree, scope)
    return {mid: _named(mid, tree, scope) for mid, tree in approach["measures"].items()}


def _named(name: str, tree: Any, scope: Mapping[str, float]) -> float:
    try:
        return formula.evaluate(tree, scope)
    except formula.FormulaError as exc:
        raise formula.FormulaError(f"{name}: {exc}") from exc


def results(spec: Mapping[str, Any]) -> Results:
    """Every approach at its own settings in every scenario."""
    out: Results = {}
    for scenario in spec["scenarios"]:
        given = inputs_of(spec, scenario)
        out[scenario["id"]] = {}
        for approach in spec["approaches"]:
            values = {**given, **settings_for(spec, approach)}
            try:
                out[scenario["id"]][approach["id"]] = measure(approach, values)
            except formula.FormulaError as exc:
                raise formula.FormulaError(
                    f"approach {approach['id']} in scenario {scenario['id']}, {exc}"
                ) from exc
    return out


def swings(spec: Mapping[str, Any]) -> list[Swing]:
    """Each control moved alone from its lowest to its highest value, in the first scenario."""
    out: list[Swing] = []
    given = inputs_of(spec, spec["scenarios"][0])
    for approach in spec["approaches"]:
        base = {**given, **settings_for(spec, approach)}
        for control in (*spec["inputs"], *reader.settings_of(spec, approach["id"])):
            ends = []
            for end in (control["min"], control["max"]):
                try:
                    ends.append(measure(approach, {**base, control["id"]: end}))
                except formula.FormulaError as exc:
                    raise formula.FormulaError(
                        f"approach {approach['id']} with {control['id']} at {end:g}, {exc}"
                    ) from exc
            out.extend(
                Swing(control["id"], approach["id"], mid, ends[0][mid], ends[1][mid])
                for mid in approach["measures"]
            )
    return out


def run(text: str, facts: Mapping[str, Any], report: Report) -> Run | None:
    """Read a solutions file's text, check it and simulate it; None when it has errors."""
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        report.errors.append(f"solutions: line {exc.lineno}: invalid JSON, {exc.msg}")
        return None
    spec = reader.read(raw, facts, report)
    if spec is None:
        return None
    try:
        found = Run(spec, results(spec), swings(spec))
    except formula.FormulaError as exc:
        report.errors.append(f"solutions: {exc}")
        return None
    for control in (*spec["inputs"], *spec["settings"]):
        moved = [s for s in found.swings if s.control == control["id"]]
        if all(s.low == s.high for s in moved):
            report.warnings.append(
                f"solutions: {control['id']} changes no measure from its min to its max"
            )
    return found
