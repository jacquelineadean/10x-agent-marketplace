"""Rigs: a figure drawn in parts, painted on its own sheets, moved by its gait."""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path
from typing import Any

import pytest
from chronicle.core.story import plates
from chronicle.core.watercolor.svg.paint import paint_drawing
from chronicle.core.watercolor.svg.parse import SvgError, parse
from chronicle_engine import registry
from chronicle_engine.connectors.files import store
from chronicle_engine.core.motion import render
from chronicle_engine.core.story import derive
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Builder

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
# An 800-wide drawing paints at 1600, so every length below doubles.
HOG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500">
  <rect width="800" height="500" fill="#e8dcc0"/>
  <g data-rig="hog" data-gait="graze" data-foot="300 400" data-roam="100 600"
     transform="translate(100 0)">
    <g data-part="leg-front" data-pivot="210 330" data-phase="0.5">
      <rect x="200" y="320" width="20" height="80" fill="#5a4636"/></g>
    <g data-part="body"><ellipse cx="250" cy="300" rx="90" ry="45" fill="#6b5444"/></g>
    <g data-part="head" data-down="25" data-pivot="330 290">
      <circle cx="350" cy="290" r="30" fill="#6b5444"/></g>
    <g data-part="snout" data-role="tail" data-amp="7">
      <rect x="370" y="285" width="20" height="10" fill="#6b5444"/></g>
  </g>
</svg>"""


def test_parts_take_roles_from_their_names_and_pivots_follow_the_drawing() -> None:
    d = parse(HOG)
    names = [layer.name for layer in d.layers]
    assert names == ["hog--leg-front", "hog--body", "hog--head", "hog--snout"]
    leg, body, head, snout = d.layers
    assert leg.rig == "hog" and leg.part["role"] == "leg"
    assert leg.part["amp"] == pytest.approx(18) and leg.part["phase"] == pytest.approx(0.5)
    assert leg.pivot == pytest.approx((620, 660))
    assert body.part["role"] == "static" and body.pivot is None
    assert head.part == {
        "role": "head",
        "name": "head",
        "down": 25,
        "nod": 3,
        "look": 2,
        "phase": 0,
    }
    assert snout.part["role"] == "tail" and snout.part["amp"] == pytest.approx(7)
    rig = d.rigs["hog"]
    assert rig.gait == "graze"
    assert (rig.bob, rig.speed, rig.stride) == pytest.approx((4, 60, 120))
    assert rig.foot == pytest.approx((800, 800))
    assert rig.roam == pytest.approx((400, 1400))


def _wrap(inner: str) -> str:
    return f'<svg viewBox="0 0 400 400">{inner}</svg>'


RECT = '<rect width="9" height="9"/>'


@pytest.mark.parametrize(
    ("inner", "message"),
    [
        (f'<g data-part="leg">{RECT}</g>', "needs a data-rig group"),
        (f'<g data-rig="a"><g data-layer="b">{RECT}</g></g>', "use data-part"),
        (f'<g data-layer="a"><g data-rig="b">{RECT}</g></g>', "inside a layer or another rig"),
        (f'<g data-rig="a"><g data-rig="b">{RECT}</g></g>', "inside a layer or another rig"),
        (f'<g data-rig="a" data-gait="gallop">{RECT}</g>', "gallop"),
        (f'<g data-rig="a"><g data-part="x" data-role="fin">{RECT}</g></g>', "fin"),
        (
            f'<g data-rig="a"><g data-part="leg">{RECT}</g><g data-part="leg">{RECT}</g></g>',
            "used twice",
        ),
        (f'<g data-rig="a">{RECT}</g><g data-rig="a">{RECT}</g>', "used twice"),
        (f'<g data-rig="a"><g data-part="x" data-pivot="3">{RECT}</g></g>', "two numbers"),
        (
            f'<g data-rig="a"><g data-part="x"><g data-part="y">{RECT}</g></g></g>',
            "inside another part",
        ),
    ],
)
def test_parse_refuses_a_rig_it_cannot_move(inner: str, message: str) -> None:
    with pytest.raises(SvgError, match=message):
        parse(_wrap(inner))


def test_a_rig_closes_at_the_end_of_its_group() -> None:
    d = parse(_wrap(f'<g data-rig="a"><g data-part="x">{RECT}</g></g><g data-layer="b">{RECT}</g>'))
    assert [(layer.name, layer.rig) for layer in d.layers] == [("a--x", "a"), ("b", "")]


def test_each_part_paints_opaque_on_its_own_sheet() -> None:
    painting = paint_drawing(parse(HOG), seed=3, scale=0.2)
    assert [layer.name for layer in painting.layers][:1] == ["hog--leg-front"]
    assert {layer.blend for layer in painting.layers} == {"normal"}
    leg = painting.layers[0]
    assert leg.image.shape[2] == 4 and leg.pivot == pytest.approx((620, 660))
    assert painting.rigs == {
        "hog": {
            "gait": "graze",
            "bob": 4.0,
            "speed": 60.0,
            "stride": 120.0,
            "foot": [800.0, 800.0],
            "roam": [400.0, 1400.0],
        }
    }


ENTRY: dict[str, Any] = {
    "file": "art/woods.webp",
    "width": 1600,
    "height": 1000,
    "anchors": {},
    "labels": [],
    "layers": [
        {
            "name": "hog--leg",
            "file": "art/woods--hog--leg.webp",
            "box": [600, 600, 40, 200],
            "rig": "hog",
            "part": {"role": "leg", "name": "leg", "amp": 18, "phase": 0.5},
            "pivot": [620, 610],
        },
        {
            "name": "hog--body",
            "file": "art/woods--hog--body.webp",
            "box": [400, 400, 400, 300],
            "rig": "hog",
            "part": {"role": "static", "name": "body", "phase": 0},
        },
    ],
    "rigs": {"hog": {"gait": "walk", "bob": 4, "speed": 60, "stride": 120, "roam": [400, 1400]}},
}


def _builder(story: dict[str, Any]) -> Builder:
    return Builder(story, {}, {"woods": ENTRY}, store.fonts())


def test_a_plate_gathers_a_rig_into_one_figure_with_pivots_as_origins(
    story: dict[str, Any],
) -> None:
    b = _builder(story)
    html = plates.plate(b, "woods")
    assert html.count('class="rig"') == 1 and html.count('class="part"') == 2
    rig = re.search(r'<span class="rig"[^>]*>', html)
    assert rig is not None
    # The rig box spans its parts: x 400 to 800 and y 400 to 800 of a 1600 by 1000 painting.
    assert 'style="left:25.000%;top:40.000%;width:25.000%;height:40.000%"' in rig.group(0)
    assert 'data-gait="walk"' in rig.group(0) and 'data-roam="25.00 87.50"' in rig.group(0)
    assert 'data-foot="50.0"' in rig.group(0)
    leg = re.search(r'<img class="part"[^>]*data-role="leg"[^>]*>', html)
    assert leg is not None
    assert 'data-amp="18"' in leg.group(0) and 'data-phase="0.5"' in leg.group(0)
    # The pivot sits 20 px into the 40 px leg and 10 px down its 200 px.
    assert "transform-origin:50.0% 5.0%" in leg.group(0)
    fid = rig.group(0).split('data-fig="')[1].split('"')[0]
    assert b.figs[fid] == {"type": "rig", "name": "hog"}
    assert {"art/woods--hog--leg.webp", "art/woods--hog--body.webp"} <= set(b.art_files)


def test_only_pages_with_rigs_ship_the_rig_parts() -> None:
    assert "js/33-rigs.js" not in registry.page_parts(["plate"])
    assert {"js/33-rigs.js", "css/15-rigs.css"} <= set(registry.page_parts(["plate", "rig"]))


def _scene_animation(gait: str) -> str:
    anim = json.loads((EXAMPLES / "animation-scene" / "animation.json").read_text("utf-8"))
    raw = json.loads((EXAMPLES / "keystone" / "facts.json").read_text("utf-8"))
    painting = {
        **ENTRY,
        "anchors": {"clock": [600, 200], "pile": [1200, 600], "lever": [400, 380]},
        "rigs": {"hog": {**ENTRY["rigs"]["hog"], "gait": gait}},
    }
    hrefs = {"art/woods.webp": "data:,"} | {layer["file"]: "data:," for layer in ENTRY["layers"]}
    sources = render.Sources(painting=painting, images=hrefs)
    css = store.asset_parts("motion", ".css") + store.asset("css/40-drawn.css")
    return render.render(anim, derive.apply(raw), store.fonts(), css, sources).svg


def test_a_walking_rig_swings_its_legs_about_the_pivot_and_bobs() -> None:
    svg = _scene_animation("walk")
    # The origin counts from the part's own box, as fill-box transforms do.
    assert "transform-box: fill-box; transform-origin: 20.0px 10.0px;" in svg
    turns = [float(v) for v in re.findall(r"rotate: (-?\d+\.\d+)deg", svg)]
    assert max(turns) == pytest.approx(18, abs=0.5) and min(turns) == pytest.approx(-18, abs=0.5)
    lifts = [float(v) for v in re.findall(r"translate: 0(?:\.0+)?px (-?\d+\.\d+)px", svg)]
    assert min(lifts) == pytest.approx(-4, abs=0.2) and max(lifts) <= 0


def test_a_still_rig_keeps_its_legs_planted() -> None:
    svg = _scene_animation("still")
    assert "rotate:" not in svg and "translate: 0px -" not in svg


RIG_ANIMATION: dict[str, Any] = {
    "schema_version": 1,
    "kind": "rig",
    "meta": {"title": "A hog trots", "description": "A hog in parts trots in place."},
    "rig": {"art": {"svg": "hog.svg", "seed": 1}, "gait": "walk"},
    "steps": [{"caption": "A trot."}],
}


def test_a_rig_animation_plays_the_gait_it_names() -> None:
    painting = {**ENTRY, "rigs": {"hog": {**ENTRY["rigs"]["hog"], "gait": "still"}}}
    hrefs = {"art/woods.webp": "data:,"} | {layer["file"]: "data:," for layer in ENTRY["layers"]}
    css = store.asset_parts("motion", ".css") + store.asset("css/40-drawn.css")
    sources = render.Sources(painting=painting, images=hrefs)
    walked = render.render(RIG_ANIMATION, {}, store.fonts(), css, sources).svg
    # The drawing says still; the animation's walk swings the leg about its pivot.
    assert "transform-origin: 20.0px 10.0px;" in walked and "rotate:" in walked
    still = copy.deepcopy(RIG_ANIMATION)
    del still["rig"]["gait"]
    assert "rotate:" not in render.render(still, {}, store.fonts(), css, sources).svg


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"rig": {"art": {"svg": "hog.svg"}, "gait": "gallop"}}, "rig.gait must be one of"),
        ({"rig": {"art": {"svg": "hog.svg"}, "spots": []}}, "rig.spots is unknown"),
        ({"rig": {"art": {"preset": "harbor"}}}, "rig.art needs an svg"),
        ({"steps": [{"caption": "x", "focus": ["hog"]}]}, "steps take captions, not focus"),
    ],
)
def test_a_rig_animation_check_names_the_problem(change: dict[str, Any], message: str) -> None:
    anim = {**copy.deepcopy(RIG_ANIMATION), **change}
    report = Report()
    registry.KINDS["rig"].check(anim, {}, render.Sources(drawing=HOG), report)
    assert any(message in error for error in report.errors), report.errors


def test_a_rig_animation_needs_a_drawing_with_a_rig() -> None:
    report = Report()
    flat = '<svg viewBox="0 0 400 300"><rect width="40" height="30"/></svg>'
    registry.KINDS["rig"].check(RIG_ANIMATION, {}, render.Sources(drawing=flat), report)
    assert report.errors == ["rig.art draws no data-rig group to move"]
