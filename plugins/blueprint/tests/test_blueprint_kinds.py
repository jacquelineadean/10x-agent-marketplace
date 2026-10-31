"""The sequence and ERD kinds, the schema reshaper and the architecture part lookup."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import pytest
from blueprint.core import architecture, erd, schema, sequence
from blueprint_helpers import EXAMPLES
from chronicle_engine.core.story.diagram import sanitize
from chronicle_engine.core.story.model import Report


def _anim(name: str) -> dict[str, Any]:
    data: dict[str, Any] = json.loads(
        (EXAMPLES / name / "animation.json").read_text(encoding="utf-8")
    )
    return data


def test_a_sequence_draws_a_lifeline_per_participant_and_an_arrow_per_message() -> None:
    spec = _anim("checkout-sequence")["sequence"]
    svg = sequence.draw(spec)
    sanitize(svg, "t")  # the drawing passes the same sanitizer as one Claude draws
    assert svg.count('<g id="p-') == 5
    assert svg.count('class="line dashed"') == 5 + 2  # lifelines and the two replies
    for k in range(1, 8):
        assert f'id="m{k}-path"' in svg
    steps = sequence.default_steps(spec)
    assert len(steps) == 7 and steps[0]["show"][0] == "p-web"


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"participants": [{"id": "a"}]}, "at least two"),
        ({"messages": [{"from": "web", "to": "nobody", "label": "x"}]}, "to names no participant"),
        ({"messages": [{"from": "web", "to": "api", "kind": "fax"}]}, "kind must be one of"),
    ],
)
def test_sequence_errors_say_what_to_change(change: dict[str, Any], message: str) -> None:
    spec = {
        "participants": [{"id": "web"}, {"id": "api"}],
        "messages": [{"from": "web", "to": "api"}],
    }
    report = Report()
    sequence.validate({**spec, **change}, report)
    assert any(message in e for e in report.errors), report.errors


def test_an_erd_draws_each_table_and_each_relation_in_the_gaps() -> None:
    spec = _anim("orders-erd")["erd"]
    svg = erd.draw(spec)
    sanitize(svg, "t")
    assert svg.count('<g id="e-') == 5 and svg.count('id="r') == 8  # group and path per relation
    assert [s.get("show") or s.get("draw") for s in erd.default_steps(spec)][1] == [
        "r1",
        "r2",
        "r3",
        "r4",
    ]


def test_erd_relations_name_real_columns() -> None:
    report = Report()
    erd.validate(
        {
            "entities": [{"id": "a", "columns": [{"name": "id"}]}],
            "relations": [{"from": "a.x", "to": "a.id"}],
        },
        report,
    )
    assert report.errors == ["erd.relations[0].from must name table.column"]


def test_schema_rows_become_the_example_erd() -> None:
    with (EXAMPLES / "orders-erd" / "schema.csv").open(encoding="utf-8") as handle:
        made = schema.erd(csv.DictReader(handle))
    example = _anim("orders-erd")["erd"]
    for relation in example["relations"]:
        relation.pop("label", None)
    assert made == example


def test_architecture_finds_parts_under_each_kind_prefix(tmp_path: Path) -> None:
    svg = '<svg class="chr-a chr-a-a-x"><g id="a-x-n-orders"/><g id="a-x-d-p1"/></svg>'
    assert architecture.slug_of(svg) == "a-x"
    assert architecture.has_part(svg, "orders") and architecture.has_part(svg, "p1")
    assert not architecture.has_part(svg, "payments")
