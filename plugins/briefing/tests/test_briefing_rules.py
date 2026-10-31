"""KPI status rules, slices and briefing's checks, as pure functions."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest
from briefing.core import animation, checks, kpi, slices
from chronicle_engine.core.story.model import Report

FACTS: dict[str, Any] = {
    "d": {
        "deploys": {"value": 37, "unit": "per week", "source": "github", "query": "q1"},
        "lead": {"value": 1.6, "unit": "days", "source": "github"},
        "name": {"value": "Keystone", "source": "github", "query": "q2"},
        "payments": {"x": {"value": 4, "source": "github", "query": "q3"}},
    }
}


@pytest.mark.parametrize(
    ("value", "target", "better", "expected"),
    [
        (37, 30, "up", "good"),
        (28, 30, "up", "warn"),
        (20, 30, "up", "bad"),
        (1.6, 2, "down", "good"),
        (2.1, 2, "down", "warn"),
        (3, 2, "down", "bad"),
        (37, None, "up", "none"),
        (37, 30, "sideways", "none"),
    ],
)
def test_status_is_set_by_rule(
    value: float, target: float | None, better: str, expected: str
) -> None:
    assert kpi.status(value, target, better, 10) == expected


def test_numbers_come_from_refs_or_literals() -> None:
    assert kpi.number(FACTS, "@d.deploys") == 37.0
    assert kpi.number(FACTS, 30) == 30.0
    assert kpi.number(FACTS, "@d.name") is None


def test_tiles_sit_in_rows_of_three_or_four() -> None:
    assert [kpi.columns(n) for n in range(1, 10)] == [1, 2, 3, 4, 3, 3, 4, 4, 3]


def test_a_sliced_block_has_one_copy_per_option() -> None:
    spec = {"key": "team", "options": {"payments": "Payments", "search": "Search"}}
    block = {"type": "chart", "slice": "team", "id": "x", "data": {"v": "@d.{team}.x"}}
    copies = dict(slices.variants(block, spec))
    assert copies["search"] == {"type": "chart", "data": {"v": "@d.search.x"}}
    assert slices.default(spec) == "payments"


def _story(*blocks: dict[str, Any], layout: str = "dashboard") -> dict[str, Any]:
    return {"layout": layout, "chapters": [{"id": "a", "title": "A", "blocks": list(blocks)}]}


def test_a_kpi_needs_a_target_a_direction_a_number_and_a_query() -> None:
    report = Report()
    items = [
        {"label": "Deploys", "value": "@d.deploys", "target": 30, "better": "up"},
        {"label": "Lead", "value": "@d.lead", "better": "down"},
        {"label": "Name", "value": "@d.name", "target": 1},
    ]
    checks.kpis(_story({"type": "kpi", "items": items}), FACTS, report)
    assert report.errors == [
        "KPI 'Lead' needs a target, a number or a fact",
        "KPI 'Name' needs better: up or down",
        "KPI 'Name': @d.name must be a number",
    ]
    assert report.warnings == [
        "KPI 'Lead': no query behind @d.lead; gather it with sources or say where it came "
        "from in its note"
    ]


def test_sliced_blocks_name_a_filter_and_real_facts() -> None:
    report = Report()
    filters = {
        "type": "filters",
        "by": [{"key": "team", "options": {"payments": "P", "search": "S"}}],
    }
    good = {"type": "prose", "slice": "team", "text": "{{d.{team}.x}} deploys"}
    lost = {"type": "prose", "slice": "region", "text": "x"}
    checks.sliced(_story(filters, good, lost), FACTS, report)
    assert any("(team=search)" in e and "no fact 'd.search.x'" in e for e in report.errors)
    assert not any("(team=payments)" in e for e in report.errors)
    assert any("slice 'region' names no filter" in e for e in report.errors)


def test_slides_say_what_does_not_fit() -> None:
    report = Report()
    words = " ".join(["word"] * 70)
    blocks = [{"type": "prose", "text": words}, *[{"type": "scrolly"}] * 4]
    story = _story(*blocks, layout="deck")
    story["chapters"][0]["title"] = "T" * 90
    checks.slides(story, report)
    assert [w.split(": ", 1)[1] for w in report.warnings] == [
        "title runs 90 characters; keep it under 80",
        "5 blocks; a slide holds 4 at most",
        "70 words; a slide holds about 60",
        *["scrolly needs a scrolling page; use a stepper"] * 4,
    ]


def test_stale_facts_warn_once_per_system() -> None:
    report = Report()
    entries = {
        "a": {"system": "github", "as_of": "2026-10-14"},
        "b": {"system": "github", "as_of": "2026-10-28"},
        "c": {"system": "jira", "as_of": "2026-10-01"},
    }
    checks.stale(entries, date(2026, 10, 31), report)
    assert report.warnings == ["jira facts are as of 2026-10-01, 30 days old; gather them again"]


def test_an_animation_file_must_be_a_built_animation() -> None:
    ok = '<svg data-steps="0,2" data-end="4"><g/></svg>'
    assert animation.lint(ok) == []
    assert animation.lint('<svg data-steps="0"><script>x()</script></svg>') == [
        "holds a script, an event handler or foreign markup"
    ]
    assert animation.lint("<svg/>")[-1].startswith("has no data-steps")
