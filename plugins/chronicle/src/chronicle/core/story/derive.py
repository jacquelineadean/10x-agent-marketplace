"""Derived facts: arithmetic done by code, never by the model.

A facts file may carry a `derive` table. Each entry names the fact to create, a function
and its inputs (dotted paths to other facts). `chronicle build` runs these before
checking the story, so a forecast or a percent change is always recomputed from the
gathered series and cites how it was made:

    "derive": {
      "plan.velocity_recent": {"fn": "mean_last", "of": "plan.velocity", "n": 6,
                               "unit": "pts", "source": "jira"},
      "plan.forecast_finish": {"fn": "burnup_finish", "done": "plan.done",
                               "scope": "plan.scope", "dates": "plan.sprint_end",
                               "window": 6, "sprint_days": 14, "source": "jira"}
    }
"""

from __future__ import annotations

import copy
import math
from collections.abc import Callable, Mapping
from datetime import date, timedelta
from typing import Any

from chronicle.core.story.facts import FactError, lookup

Args = Mapping[str, Any]


def _series(facts: Mapping[str, Any], path: str) -> list[float]:
    values = lookup(facts, path).value
    if not isinstance(values, list) or not values:
        raise FactError(f"{path} must be a non-empty list of numbers")
    return [float(v) for v in values if v is not None]


def _number(facts: Mapping[str, Any], path: str) -> float:
    value = lookup(facts, path).value
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise FactError(f"{path} must be a number, got {value!r}")
    return float(value)


def _tidy(value: float) -> float | int:
    rounded = round(value, 2)
    return int(rounded) if float(rounded).is_integer() else rounded


def last(facts: Mapping[str, Any], args: Args) -> Any:
    """The final value of a series."""
    return _tidy(_series(facts, args["of"])[-1])


def mean_last(facts: Mapping[str, Any], args: Args) -> Any:
    """Mean of the last n values of a series (default 6), rounded to whole units."""
    values = _series(facts, args["of"])[-int(args.get("n", 6)) :]
    return round(sum(values) / len(values))


def growth_last(facts: Mapping[str, Any], args: Args) -> Any:
    """Average step between the last n+1 values of a cumulative series."""
    n = int(args.get("n", 6))
    values = _series(facts, args["of"])
    if len(values) <= n:
        raise FactError(f"{args['of']} needs more than {n} values")
    return round((values[-1] - values[-1 - n]) / n)


def pct_change(facts: Mapping[str, Any], args: Args) -> Any:
    """Percent change from `from` to `to`, rounded to a whole percent."""
    start, end = _number(facts, args["from"]), _number(facts, args["to"])
    if start == 0:
        raise FactError(f"{args['from']} is zero; percent change is undefined")
    return round((end - start) / abs(start) * 100)


def ratio(facts: Mapping[str, Any], args: Args) -> Any:
    """`of` divided by `to`, to one decimal place below 10 and whole numbers above."""
    top, bottom = _number(facts, args["of"]), _number(facts, args["to"])
    if bottom == 0:
        raise FactError(f"{args['to']} is zero; the ratio is undefined")
    value = top / bottom
    return round(value) if abs(value) >= 10 else round(value, 1)


def diff(facts: Mapping[str, Any], args: Args) -> Any:
    """`of` minus `minus`."""
    return _tidy(_number(facts, args["of"]) - _number(facts, args["minus"]))


def share(facts: Mapping[str, Any], args: Args) -> Any:
    """`of` as a whole percent of `to`."""
    whole = _number(facts, args["to"])
    if whole == 0:
        raise FactError(f"{args['to']} is zero; the share is undefined")
    return round(_number(facts, args["of"]) / whole * 100)


def total(facts: Mapping[str, Any], args: Args) -> Any:
    """Sum of a series."""
    return _tidy(sum(_series(facts, args["of"])))


def _burnup(facts: Mapping[str, Any], args: Args) -> tuple[int, date]:
    done = _series(facts, args["done"])
    scope = _series(facts, args["scope"])
    window = int(args.get("window", 6))
    if len(done) <= window or len(scope) <= window:
        raise FactError(f"burnup needs more than {window} sprints of done and scope")
    velocity = round((done[-1] - done[-1 - window]) / window)
    growth = round((scope[-1] - scope[-1 - window]) / window)
    if velocity <= growth:
        raise FactError("scope grows as fast as work is done; the burnup never finishes")
    sprints = math.ceil((scope[-1] - done[-1]) / (velocity - growth))
    dates = lookup(facts, args["dates"]).value
    end = date.fromisoformat(str(dates[-1]))
    return sprints, end + timedelta(days=int(args.get("sprint_days", 14)) * sprints)


def burnup_sprints(facts: Mapping[str, Any], args: Args) -> Any:
    """Sprints until done meets scope, projecting the recent pace and scope growth."""
    return _burnup(facts, args)[0]


def burnup_finish(facts: Mapping[str, Any], args: Args) -> Any:
    """ISO date the burnup lines meet, matching the page's own projection."""
    return _burnup(facts, args)[1].isoformat()


def weeks_between(facts: Mapping[str, Any], args: Args) -> Any:
    """Whole weeks from date `from` to date `to` (negative when `to` is earlier)."""
    start = date.fromisoformat(str(lookup(facts, args["from"]).value))
    end = date.fromisoformat(str(lookup(facts, args["to"]).value))
    return round((end - start).days / 7)


FUNCTIONS: dict[str, Callable[[Mapping[str, Any], Args], Any]] = {
    "last": last,
    "mean_last": mean_last,
    "growth_last": growth_last,
    "pct_change": pct_change,
    "ratio": ratio,
    "diff": diff,
    "share": share,
    "total": total,
    "burnup_sprints": burnup_sprints,
    "burnup_finish": burnup_finish,
    "weeks_between": weeks_between,
}
RECORD_KEYS = ("unit", "source", "note")


def apply(facts: Mapping[str, Any]) -> dict[str, Any]:
    """Return a copy of the facts with every `derive` entry computed, in order."""
    out: dict[str, Any] = copy.deepcopy(dict(facts))
    for target, spec in dict(out.get("derive", {})).items():
        name = str(spec.get("fn", ""))
        if name not in FUNCTIONS:
            raise FactError(f"derive {target}: unknown fn {name!r}; use {', '.join(FUNCTIONS)}")
        try:
            value = FUNCTIONS[name](out, spec)
        except KeyError as exc:
            raise FactError(f"derive {target}: {name} needs {exc.args[0]!r}") from exc
        except FactError as exc:
            raise FactError(f"derive {target}: {exc}") from exc
        record: dict[str, Any] = {"value": value}
        record.update({k: spec[k] for k in RECORD_KEYS if k in spec})
        record.setdefault("note", f"computed: {name}")
        _place(out, target, record)
    return out


def _place(facts: dict[str, Any], path: str, record: dict[str, Any]) -> None:
    node = facts
    parts = path.split(".")
    for part in parts[:-1]:
        child = node.setdefault(part, {})
        if not isinstance(child, dict):
            raise FactError(f"derive {path}: {part} is a value, not a group")
        node = child
    node[parts[-1]] = record
