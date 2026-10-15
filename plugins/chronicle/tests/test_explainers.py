from __future__ import annotations

import copy
import json
import re
from typing import Any

import pytest
from chronicle.core.story import model
from chronicle.core.story.diagram import DiagramError, sanitize
from chronicle.core.story.render import Assets, render

DIAGRAM = """<svg viewBox="0 0 400 200">
  <defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5"><path d="M0 0 L10 5 L0 10 Z"/>
  </marker></defs>
  <g id="cart" data-tip="Cart lag {{reliability.incident_lag|compact}}">
    <rect class="box accent" x="10" y="10" width="120" height="60"/>
    <text x="70" y="45" text-anchor="middle">Cart &amp; checkout</text>
  </g>
  <path class="line" d="M130 40 L200 40" marker-end="url(#arrow)"/>
</svg>"""


def test_diagram_keeps_allowed_markup_and_namespaces_ids() -> None:
    d = sanitize(
        DIAGRAM, "dg7", lambda s: s.replace("{{reliability.incident_lag|compact}}", "400K")
    )
    assert 'id="dg7-cart"' in d.markup and 'marker-end="url(#dg7-arrow)"' in d.markup
    assert 'data-tip="Cart lag 400K"' in d.markup and 'tabindex="0"' in d.markup
    assert "Cart &amp; checkout" in d.markup
    assert d.ids == {"arrow", "cart"} and d.tips == 1


@pytest.mark.parametrize(
    ("svg", "message"),
    [
        ('<svg viewBox="0 0 9 9"><script>alert(1)</script></svg>', "<script> is not allowed"),
        ('<svg viewBox="0 0 9 9"><foreignObject/></svg>', "not allowed"),
        ('<svg viewBox="0 0 9 9"><rect onclick="x()"/></svg>', "onclick"),
        ('<svg viewBox="0 0 9 9"><rect style="fill:red"/></svg>', "style"),
        ('<svg viewBox="0 0 9 9"><use href="https://evil.example/x.svg#a"/></svg>', "href"),
        ('<svg viewBox="0 0 9 9"><rect fill="url(javascript:x)"/></svg>', "characters"),
        ("<svg><rect/></svg>", "viewBox"),
        ('<!DOCTYPE x><svg viewBox="0 0 9 9"/>', "DOCTYPE"),
    ],
)
def test_diagram_sanitizer_refuses_anything_outside_the_allowlist(svg: str, message: str) -> None:
    with pytest.raises(DiagramError, match=message):
        sanitize(svg, "dg1")


def add_blocks(story: dict[str, Any]) -> dict[str, Any]:
    changed = copy.deepcopy(story)
    changed["chapters"][0]["blocks"] += [
        {
            "type": "tilemap",
            "title": "By state",
            "frames": ["2026-06", "2026-07"],
            "values": {"NV": [10, 100], "OR": [0, 60]},
            "scale": {"min": 0, "max": 100},
            "readout": {"text": "{frame}: {count} of {total}", "count": {"gte": 100}},
        },
        {
            "type": "quiz",
            "title": "Check yourself",
            "questions": [
                {
                    "q": "Which moved first?",
                    "options": ["Cart", "Catalog"],
                    "answer": 1,
                    "explain": "Catalog, on {{migration.catalog_live|date}}.",
                }
            ],
            "results": [{"min": 0, "label": "Keep going"}, {"min": 1, "label": "Perfect"}],
        },
        {
            "type": "checklist",
            "title": "Week one",
            "groups": [{"title": "Day 1", "items": ["Get a laptop", "Ship a change"]}],
        },
        {
            "type": "widget",
            "name": "pack-drill",
            "script": "w/pack.js",
            "data": {"n": 3},
            "fallback": "A packing drill.",
        },
    ]
    return changed


def test_new_blocks_render_static_html_and_register_their_data(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    files = {**assets.files, "w/pack.js": "root.textContent = String(data.n);"}
    page = render(add_blocks(story), facts, {}, Assets(assets.css, assets.js, assets.fonts, files))
    html = page.fragment
    raw = re.search(r'id="chronicle-data">(.*?)</script>', html)
    assert raw
    figs = json.loads(raw.group(1))["figs"].values()
    tilemap = next(f for f in figs if f.get("type") == "tilemap")
    assert len(tilemap["tiles"]) == 51 and tilemap["values"]["NV"] == [10, 100]
    quiz = next(f for f in figs if f.get("type") == "quiz")
    assert quiz["answers"] == [1] and quiz["results"][1]["label"] == "Perfect"
    assert 'class="qz-opt"' in html and 'class="qz-explain"' in html and "21 Jul 2025" in html
    assert html.count('type="checkbox"') == 2
    assert '["pack-drill"] = function (root, data, kit)' in html
    assert 'class="mark mark-label"' in html


def test_check_catches_bad_quizzes_maps_and_widget_names(
    story: dict[str, Any], facts: dict[str, Any]
) -> None:
    changed = add_blocks(story)
    blocks = changed["chapters"][0]["blocks"]
    blocks[-3]["questions"][0]["answer"] = 5
    blocks[-4]["layout"] = "custom"
    blocks[-1]["name"] = "Pack Drill"
    errors = " ".join(model.check(changed, facts).errors)
    assert "answer must index its options" in errors
    assert "custom tilemap needs tiles" in errors
    assert "name must be lowercase" in errors


def test_widget_lint_names_each_forbidden_call() -> None:
    script = "root.innerHTML = data.x; fetch('https://x.example'); localStorage.x = 1;"
    problems = " ".join(model.lint_widget(script))
    assert "innerHTML" in problems and "fetch" in problems and "kit.store" in problems
    assert model.lint_widget("kit.html('p', null, data.text, root);") == []
    assert model.lint_style("@import url(x.css);")
