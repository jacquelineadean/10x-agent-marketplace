"""The solutions file: approaches to one design question, the inputs and settings a reader
moves, the scenarios, and the measures each approach computes by formula.

`read` checks what Claude wrote and returns the plain form the simulator and the page
share: fact references filled in, switches and choices as numbers, and each approach's
formulas as trees in the order they evaluate.
"""

from __future__ import annotations

import keyword
import math
import re
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.facts import FactError, resolve_refs
from chronicle_engine.core.story.model import Report, check_text

from blueprint.core.solutions import formula

ID = re.compile(r"^[a-z][a-z0-9_]{0,30}$")
KINDS = ("number", "toggle", "choice")
BETTER = ("lower", "higher")
# What a reader can feel and the units it reads: a wait in real time, failures out of 100.
FEELS: dict[str, tuple[str, ...]] = {"wait": ("ms", "s"), "failures": ("%",)}
# The page lays variants out as columns; more than six do not fit a desktop screen.
MOST_VARIANTS = 6
TEXT_KEYS = ("title", "question", "label", "text", "note", "action")


def read(raw: Any, facts: Mapping[str, Any], report: Report) -> dict[str, Any] | None:
    """The checked, plain form of a solutions file, or None when it has errors."""
    start = len(report.errors)
    if not isinstance(raw, Mapping):
        report.errors.append("solutions: the file must hold a JSON object")
        return None
    _texts(raw, "solutions", facts, report)
    try:
        data = resolve_refs(dict(raw), facts)
    except FactError as exc:
        report.errors.append(f"solutions: {exc}")
        return None
    approach_ids = [str(a.get("id", "")) for a in _items(data, "approaches", report)]
    if not 2 <= len(approach_ids) <= MOST_VARIANTS:
        report.errors.append(f"solutions.approaches needs 2 to {MOST_VARIANTS} approaches")
    names: set[str] = set()
    inputs = [
        _control(item, f"solutions.inputs[{i}]", approach_ids, names, report, setting=False)
        for i, item in enumerate(_items(data, "inputs", report))
    ]
    settings = [
        _control(item, f"solutions.settings[{i}]", approach_ids, names, report, setting=True)
        for i, item in enumerate(_items(data, "settings", report, least=0))
    ]
    shared = _lets(data.get("let"), "solutions.let", names, report)
    names.update(shared)
    taken: set[str] = set()
    measures = [
        _measure(item, f"solutions.measures[{i}]", taken, report)
        for i, item in enumerate(_items(data, "measures", report))
    ]
    taken = set()
    by_id = {c["id"]: c for c in inputs}
    scenarios = [
        _scenario(item, f"solutions.scenarios[{i}]", taken, by_id, report)
        for i, item in enumerate(_items(data, "scenarios", report))
    ]
    taken = set()
    approaches = [
        _approach(
            item, f"solutions.approaches[{i}]", taken, inputs, settings, shared, measures, report
        )
        for i, item in enumerate(_items(data, "approaches", report))
    ]
    if len(report.errors) > start:
        return None
    return {
        "title": str(data.get("title", "")),
        "question": str(data.get("question", "")),
        "inputs": inputs,
        "settings": settings,
        "scenarios": scenarios,
        "measures": measures,
        "approaches": approaches,
        "most_variants": MOST_VARIANTS,
    }


def fits(control: Mapping[str, Any], value: float) -> bool:
    """Whether a control can hold the value: a switch position, an option or a number in range."""
    if control["kind"] == "choice":
        return any(value == option["value"] for option in control["options"])
    if control["kind"] == "toggle":
        return value in (0.0, 1.0)
    return bool(control["min"] <= value <= control["max"])


def settings_of(spec: Mapping[str, Any], approach_id: str) -> list[dict[str, Any]]:
    """The settings an approach has: the shared ones and those that name it."""
    return [s for s in spec["settings"] if not s["approaches"] or approach_id in s["approaches"]]


def number(value: Any) -> float | None:
    """A finite number as a float; None for anything else, a true or false included."""
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        return None
    return float(value)


def _texts(node: Any, where: str, facts: Mapping[str, Any], report: Report) -> None:
    """Words the page shows get the story's own check: tokens name facts, numbers need tokens."""
    if isinstance(node, Mapping):
        for key, value in node.items():
            if isinstance(value, str) and key in TEXT_KEYS:
                check_text(value, f"{where}.{key}", "text", facts, report)
            else:
                _texts(value, f"{where}.{key}", facts, report)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            _texts(value, f"{where}[{i}]", facts, report)


def _items(data: Mapping[str, Any], key: str, report: Report, least: int = 1) -> list[Any]:
    found = data.get(key, [])
    if not isinstance(found, list) or len(found) < least:
        report.errors.append(f"solutions.{key} must be a list of at least {least}")
        return []
    kept = [item for item in found if isinstance(item, Mapping)]
    if len(kept) != len(found):
        report.errors.append(f"solutions.{key} holds an entry that is not an object")
    return kept


def _id(item: Mapping[str, Any], where: str, taken: set[str], report: Report) -> str:
    found = str(item.get("id", ""))
    if not ID.match(found) or keyword.iskeyword(found) or found in formula.FUNCTIONS:
        report.errors.append(
            f"{where}.id {found!r} must be lowercase letters, digits and underscores, "
            "and not a formula word"
        )
    elif found in taken:
        report.errors.append(f"{where}.id {found!r} is used twice")
    taken.add(found)
    return found


def _decimals(item: Mapping[str, Any], where: str, report: Report, default: int) -> int:
    found = item.get("decimals", default)
    if isinstance(found, bool) or not isinstance(found, int) or not 0 <= found <= 2:
        report.errors.append(f"{where}.decimals must be 0, 1 or 2")
        return default
    return found


def _control(
    item: Mapping[str, Any],
    where: str,
    approach_ids: list[str],
    names: set[str],
    report: Report,
    *,
    setting: bool,
) -> dict[str, Any]:
    """An input or a setting: a number the reader slides, a switch or a choice."""
    cid = _id(item, where, names, report)
    kind = str(item.get("kind", "number")) if setting else "number"
    if kind not in KINDS:
        report.errors.append(f"{where}.kind must be one of {', '.join(KINDS)}")
        kind = "number"
    out: dict[str, Any] = {
        "id": cid,
        "label": str(item.get("label") or cid),
        "kind": kind,
        "unit": str(item.get("unit", "")),
        "note": str(item.get("note", "")),
        "source": str(item.get("source", "")),
        "options": [],
        "off": None,
    }
    if kind == "toggle":
        if not isinstance(item.get("value"), bool):
            report.errors.append(f"{where}.value must be true or false")
        out.update(value=float(bool(item.get("value"))), min=0.0, max=1.0, step=1.0, decimals=0)
    elif kind == "choice":
        out.update(_choice(item, where, report))
    else:
        out.update(_range(item, where, report))
    if setting:
        out["key"] = str(item.get("key", ""))
        named = [str(a) for a in item.get("approaches") or []]
        for name in named:
            if name not in approach_ids:
                report.errors.append(f"{where}.approaches names no approach {name!r}")
        out["approaches"] = named
        if "off" in item:
            out["off"] = number(item["off"])
            if kind == "toggle" or out["off"] is None:
                report.errors.append(f"{where}.off must be a number, on a number or a choice")
    return out


def _range(item: Mapping[str, Any], where: str, report: Report) -> dict[str, Any]:
    value, low, high = (number(item.get(key)) for key in ("value", "min", "max"))
    if value is None or low is None or high is None or not low < high or not low <= value <= high:
        report.errors.append(f"{where} needs numbers with min below max and value between them")
        return {"value": 0.0, "min": 0.0, "max": 1.0, "step": 1.0, "decimals": 0}
    whole = all(float(n).is_integer() for n in (value, low, high))
    step = number(item.get("step", 1.0 if whole else (high - low) / 100))
    if step is None or step <= 0:
        report.errors.append(f"{where}.step must be a number above 0")
        step = 1.0
    places = 0 if step.is_integer() else 1 if (step * 10).is_integer() else 2
    return {
        "value": value,
        "min": low,
        "max": high,
        "step": step,
        "decimals": _decimals(item, where, report, places),
    }


def _choice(item: Mapping[str, Any], where: str, report: Report) -> dict[str, Any]:
    given = [option for option in item.get("options") or [] if isinstance(option, Mapping)]
    found = [number(option.get("value")) for option in given]
    values = [value for value in found if value is not None]
    if len(values) < 2 or len(values) != len(found) or len(set(values)) != len(values):
        report.errors.append(f"{where}.options needs two or more with different number values")
        return {"value": 0.0, "min": 0.0, "max": 0.0, "step": 0.0, "decimals": 0}
    value = number(item.get("value"))
    if value not in values:
        report.errors.append(f"{where}.value must be the value of one of its options")
        value = values[0]
    return {
        "options": [
            {"label": str(option.get("label", "")), "value": option_value}
            for option, option_value in zip(given, values, strict=True)
        ],
        "value": value,
        "min": min(values),
        "max": max(values),
        "step": 0.0,
        "decimals": _decimals(item, where, report, 0),
    }


def _measure(
    item: Mapping[str, Any], where: str, taken: set[str], report: Report
) -> dict[str, Any]:
    mid = _id(item, where, taken, report)
    better = str(item.get("better", "lower"))
    if better not in BETTER:
        report.errors.append(f"{where}.better must be lower or higher")
    budget = number(item["budget"]) if "budget" in item else None
    if "budget" in item and budget is None:
        report.errors.append(f"{where}.budget must be a number")
    unit = str(item.get("unit", ""))
    feel = item.get("feel")
    if feel is not None:
        named = dict(feel) if isinstance(feel, Mapping) else {"kind": feel}
        kind = str(named.get("kind", ""))
        if kind not in FEELS:
            report.errors.append(f"{where}.feel must be one of {', '.join(FEELS)}")
        elif unit not in FEELS[kind]:
            report.errors.append(f"{where}.feel {kind} reads a unit of {' or '.join(FEELS[kind])}")
        feel = {"kind": kind, "action": str(named.get("action", ""))}
    return {
        "id": mid,
        "label": str(item.get("label") or mid),
        "unit": unit,
        "decimals": _decimals(item, where, report, 0),
        "better": better,
        "budget": budget,
        "feel": feel,
    }


def _scenario(
    item: Mapping[str, Any],
    where: str,
    taken: set[str],
    inputs: Mapping[str, Mapping[str, Any]],
    report: Report,
) -> dict[str, Any]:
    sid = _id(item, where, taken, report)
    return {
        "id": sid,
        "label": str(item.get("label") or sid),
        "text": str(item.get("text", "")),
        "inputs": values(item.get("inputs"), inputs, f"{where}.inputs", report),
    }


def values(
    given: Any, controls: Mapping[str, Mapping[str, Any]], where: str, report: Report
) -> dict[str, float]:
    """Values for named controls, each one the control can hold; errors name the others."""
    out: dict[str, float] = {}
    for key, raw in dict(given or {}).items():
        control = controls.get(str(key))
        if control is None:
            report.errors.append(f"{where}.{key} names no control here")
            continue
        switch = control["kind"] == "toggle" and isinstance(raw, bool)
        value = float(raw) if switch else number(raw)
        if value is None or not fits(control, value):
            report.errors.append(f"{where}.{key} is not a value {control['label']!r} can hold")
        else:
            out[str(key)] = value
    return out


def _lets(given: Any, where: str, names: set[str], report: Report) -> dict[str, Any]:
    """Named formulas, parsed; a name may not repeat an input, a setting or a shared name."""
    out: dict[str, Any] = {}
    for name, text in dict(given or {}).items():
        _id({"id": name}, f"{where}.{name}", set(names), report)
        out[str(name)] = _parse(text, f"{where}.{name}", report)
    return out


def _parse(text: Any, where: str, report: Report) -> Any:
    try:
        return formula.parse(str(text)) if isinstance(text, str) else _refuse(text)
    except formula.FormulaError as exc:
        report.errors.append(f"{where}: {exc}")
        return 0.0


def _refuse(text: Any) -> Any:
    raise formula.FormulaError(f"a formula is text, not {text!r}")


def _approach(
    item: Mapping[str, Any],
    where: str,
    taken: set[str],
    inputs: list[dict[str, Any]],
    settings: list[dict[str, Any]],
    shared: Mapping[str, Any],
    measures: list[dict[str, Any]],
    report: Report,
) -> dict[str, Any]:
    aid = _id(item, where, taken, report)
    own = {s["id"]: s for s in settings if not s["approaches"] or aid in s["approaches"]}
    known = {c["id"] for c in inputs} | set(own)
    lets = {**shared, **_lets(item.get("let"), f"{where}.let", known | set(shared), report)}
    written = dict(item.get("measures") or {})
    wanted = [m["id"] for m in measures]
    for extra in sorted(set(written) - set(wanted)):
        report.errors.append(f"{where}.measures.{extra} names no measure")
    trees: dict[str, Any] = {}
    for mid in wanted:
        if mid not in written:
            report.errors.append(f"{where}.measures is missing a formula for {mid!r}")
            continue
        trees[mid] = _parse(written[mid], f"{where}.measures.{mid}", report)
    return {
        "id": aid,
        "label": str(item.get("label") or aid),
        "text": str(item.get("text", "")),
        "settings": values(item.get("settings"), own, f"{where}.settings", report),
        "steps": _order(lets, trees, known, where, report),
        "measures": trees,
    }


def _order(
    lets: Mapping[str, Any],
    trees: Mapping[str, Any],
    known: set[str],
    where: str,
    report: Report,
) -> list[list[Any]]:
    """The named formulas the measures need, each after the names it reads."""
    steps: list[list[Any]] = []
    done: set[str] = set()

    def visit(name: str, path: tuple[str, ...]) -> None:
        if name in known or name in done:
            return
        if name in path:
            report.errors.append(f"{where}.let: {' -> '.join((*path, name))} is a circle")
            return
        if name not in lets:
            report.errors.append(
                f"{where}: {name!r} is not an input, a setting of this approach or a let name"
            )
            done.add(name)
            return
        for inner in sorted(formula.names(lets[name])):
            visit(inner, (*path, name))
        done.add(name)
        steps.append([name, lets[name]])

    for tree in trees.values():
        for name in sorted(formula.names(tree)):
            visit(name, ())
    return steps
