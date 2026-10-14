from __future__ import annotations

from typing import Any

import pytest
from chronicle.core.story import derive
from chronicle.core.story.facts import FactError

BASE: dict[str, Any] = {
    "plan": {
        "done": [100, 200, 300, 400],
        "scope": [1000, 1010, 1020, 1030],
        "end": ["2026-09-13", "2026-09-27", "2026-10-11", "2026-10-25"],
        "target": "2026-12-31",
    },
    "cost": {"now": {"value": 540, "unit": "$"}, "after": 205},
}


def run(spec: dict[str, Any]) -> Any:
    facts = derive.apply({**BASE, "derive": {"out.value": spec}})
    return facts["out"]["value"]


@pytest.mark.parametrize(
    ("spec", "expected"),
    [
        ({"fn": "last", "of": "plan.done"}, 400),
        ({"fn": "mean_last", "of": "plan.done", "n": 2}, 350),
        ({"fn": "growth_last", "of": "plan.scope", "n": 3}, 10),
        ({"fn": "diff", "of": "cost.now", "minus": "cost.after"}, 335),
        ({"fn": "ratio", "of": "cost.now", "to": "cost.after"}, 2.6),
        ({"fn": "share", "of": "cost.after", "to": "cost.now"}, 38),
        ({"fn": "pct_change", "from": "cost.after", "to": "cost.now"}, 163),
        ({"fn": "total", "of": "plan.done"}, 1000),
    ],
)
def test_functions(spec: dict[str, Any], expected: Any) -> None:
    assert run(spec)["value"] == expected


def test_burnup_matches_the_page_projection() -> None:
    args = {"done": "plan.done", "scope": "plan.scope", "dates": "plan.end", "window": 3}
    # 100 points a sprint against 10 added: 630 left takes 7 sprints from 25 Oct.
    assert run({"fn": "burnup_sprints", **args})["value"] == 7
    assert run({"fn": "burnup_finish", **args})["value"] == "2027-01-31"


def test_derived_record_keeps_unit_and_source() -> None:
    record = run({"fn": "last", "of": "plan.done", "unit": "pts", "source": "jira"})
    assert record == {"value": 400, "unit": "pts", "source": "jira", "note": "computed: last"}


def test_errors_name_the_entry() -> None:
    with pytest.raises(FactError, match="derive out.value: unknown fn 'median'"):
        run({"fn": "median", "of": "plan.done"})
    with pytest.raises(FactError, match="derive out.value: ratio needs 'to'"):
        run({"fn": "ratio", "of": "cost.now"})


def test_keystone_forecast(facts: dict[str, Any]) -> None:
    plan = facts["plan"]
    assert plan["forecast_finish"]["value"] == "2027-04-25"
    assert plan["forecast_weeks_late"]["value"] == 4
