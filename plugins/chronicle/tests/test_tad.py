"""TAD animations: the spec, layout and routing, the step checks and the drawn figure."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from chronicle.connectors.files import store
from chronicle.core.motion import render
from chronicle.core.motion.tad import draw, layout, route, spec
from chronicle.core.story.model import Report

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "animation-tad" / "animation.json"


@pytest.fixture
def anim() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    return data


def _read(body: dict[str, Any]) -> tuple[spec.Tad | None, Report]:
    report = Report()
    return spec.read(body, report, {}), report


def test_the_example_lays_out_with_no_overlaps(anim: dict[str, Any]) -> None:
    tad, report = _read(anim["tad"])
    assert tad is not None and report.ok
    placed = layout.place(tad, tall=False)
    assert placed.warnings == []
    rects = list(placed.nodes.items())
    for i, (a, ra) in enumerate(rects):
        for b, rb in rects[i + 1 :]:
            assert not ra.hits(rb, 8), (a, b)
    for gid in tad.groups:
        box = placed.groups[gid]
        for nid in tad.members(gid):
            r = placed.nodes[nid]
            assert box.x < r.x and r.x + r.w < box.x + box.w, (gid, nid)
            assert box.y < r.y and r.y + r.h < box.y + box.h, (gid, nid)
    # Vendors name tier 5, so their box sits right of the VPC, level with Payments.
    assert placed.groups["vendors"].x > placed.groups["cloud"].x + placed.groups["cloud"].w
    assert abs(placed.nodes["cards"].cy - placed.nodes["payments"].cy) < 60


def test_linked_nodes_sit_level_and_tiers_follow_the_edges(anim: dict[str, Any]) -> None:
    tad, _ = _read(anim["tad"])
    assert tad is not None
    placed = layout.place(tad, tall=False)
    assert [placed.tier[n] for n in ("web", "gateway", "orders", "payments")] == [0, 1, 2, 3]
    assert placed.nodes["web"].cy == placed.nodes["gateway"].cy == placed.nodes["orders"].cy


def test_routes_run_square_from_side_to_side_around_other_boxes(anim: dict[str, Any]) -> None:
    tad, _ = _read(anim["tad"])
    assert tad is not None
    placed = layout.place(tad, tall=False)
    routes = route.route_all(tad, placed)
    assert set(routes) == set(tad.edges)
    for eid, r in routes.items():
        ends = {r.edge.src, r.edge.dst}
        for (x0, y0), (x1, y1) in zip(r.points, r.points[1:], strict=False):
            assert x0 == pytest.approx(x1) or y0 == pytest.approx(y1), eid
            mid = ((x0 + x1) / 2, (y0 + y1) / 2)
            for nid, box in placed.nodes.items():
                if nid not in ends:
                    inside = box.x < mid[0] < box.x + box.w and box.y < mid[1] < box.y + box.h
                    assert not inside, (eid, nid)
        assert r.heads and r.length > 0


def test_arrowheads_are_filled_for_requests_and_open_for_events() -> None:
    assert route.arrowhead((0, 0), (10, 0), "sync").endswith("Z")
    assert not route.arrowhead((0, 0), (10, 0), "async").endswith("Z")


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda t: t["nodes"][0].update(kind="servcie"), "(did you mean service?)"),
        (lambda t: t["edges"].append({"from": "web", "to": "nowhere"}), "'nowhere' is not a node"),
        (lambda t: t["nodes"].append({"id": "web", "label": "Again"}), "is used twice"),
        (lambda t: t["flows"].append({"id": "f", "path": ["web", "db"]}), "no edge links web"),
        (lambda t: t["nodes"][0].update(lane=1), "give every node a lane"),
        (lambda t: t["groups"][0].update(parent="core"), "inside itself"),
        (lambda t: t.update(direction="left"), "tad.direction must be one of"),
    ],
)
def test_spec_errors_say_what_to_change(anim: dict[str, Any], change: Any, message: str) -> None:
    body = copy.deepcopy(anim["tad"])
    change(body)
    _, report = _read(body)
    assert any(message in e for e in report.errors), report.errors


def test_a_reversed_flow_runs_against_its_edges(anim: dict[str, Any]) -> None:
    body = copy.deepcopy(anim["tad"])
    body["flows"] = [{"id": "back", "path": ["cards", "payments"]}]
    tad, report = _read(body)
    assert tad is not None and report.ok
    ((edge, forward),) = tad.flows["back"].hops
    assert edge.src == "payments" and forward is False


def test_steps_naming_missing_parts_or_states_fail(anim: dict[str, Any]) -> None:
    tad, _ = _read(anim["tad"])
    assert tad is not None
    report = Report()
    steps = [
        {"show": ["paymnets"]},
        {"flow": ["nope"]},
        {"state": {"cards": "melting", "ghost": "down"}},
    ]
    draw.check_steps(steps, tad, report)
    text = " ".join(report.errors)
    assert "(did you mean payments?)" in text
    assert "name a tad flow or an edge" in text
    assert "state.cards must be one of" in text
    assert "states apply to nodes, edges and groups" in text


def test_without_steps_each_tier_appears_then_each_flow_runs(anim: dict[str, Any]) -> None:
    tad, _ = _read(anim["tad"])
    assert tad is not None
    steps = draw.default_steps(tad)
    assert steps[0]["show"] == ["web"]
    assert [s["flow"] for s in steps if "flow" in s] == [["place"], ["to-email"], ["to-warehouse"]]


def test_the_example_renders_one_svg_with_packets_masks_and_labels(anim: dict[str, Any]) -> None:
    css = store.asset_parts("motion", ".css") + store.asset("css/40-drawn.css")
    result = render.render(anim, {}, store.fonts(), css, render.Sources())
    svg = result.svg
    assert result.warnings == []
    assert svg.startswith("<svg") and "<script" not in svg
    assert svg.count('class="m-packet"') == 8  # one per hop of the three flows
    assert "<mask" in svg and "m-elabel" in svg
    slug = result.plan.slug
    # The label of a line drawn on later waits for the line.
    assert f"#{slug}-e-gateway-orders-l {{" in svg
    assert "prefers-reduced-motion" in svg
    assert f"{slug}-n-fraud" in svg and "PLANNED" in svg


def test_a_crowded_frame_warns_that_text_is_small(anim: dict[str, Any]) -> None:
    anim["frame"] = {"size": "1:1"}
    css = store.asset_parts("motion", ".css")
    result = render.render(anim, {}, store.fonts(), css, render.Sources())
    assert any("shrunk" in w for w in result.warnings)
