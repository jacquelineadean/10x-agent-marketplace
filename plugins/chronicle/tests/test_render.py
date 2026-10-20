from __future__ import annotations

import copy
import json
import re
from typing import Any

from chronicle.core.story.render import Assets, render

MANIFEST = {
    "hero": {
        "file": "art/hero.webp",
        "width": 1800,
        "height": 820,
        "anchors": {"hook": [1200, 204], "load": [1200, 304]},
        "layers": [
            {
                "name": "keystone",
                "file": "art/hero--keystone.webp",
                "box": [1183, 299, 34, 60],
                "motion": "descend",
                "travel": 150,
            },
        ],
    },
}


def payload(html: str) -> dict[str, Any]:
    match = re.search(r'<script type="application/json" id="chronicle-data">(.*?)</script>', html)
    assert match
    data: dict[str, Any] = json.loads(match.group(1))
    return data


def test_page_fills_every_token_and_cites_sources(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(story, facts, MANIFEST, assets)
    assert "{{" not in page.fragment
    assert '<span class="fact" tabindex="0" data-src="datadog"' in page.fragment
    assert page.fragment.startswith("<title>Keystone</title>")
    assert page.document.startswith("<!doctype html>")
    assert page.art_files == ["art/hero--keystone.webp", "art/hero.webp"]


def test_figure_specs_carry_resolved_data(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    data = payload(render(story, facts, MANIFEST, assets).fragment)
    calendar = next(f for f in data["figs"].values() if f.get("chart") == "calendar")
    assert calendar["data"]["values"] == facts["delivery"]["calendar"]
    tilemap = next(f for f in data["figs"].values() if f.get("type") == "tilemap")
    assert tilemap["values"] == facts["rollout"]["share"]
    assert "{{" not in json.dumps(data["sources"])
    assert [n["no"] for n in data["nav"]] == ["01", "02", "03", "04", "05", "06", "07"]
    assert data["progress"] == {
        "kind": "track",
        "icon": "parcel",
        "line": "belt",
        "start_label": "Order placed",
    }
    plate = next(f for f in data["figs"].values() if f.get("type") == "plate")
    assert plate["anchors"]["hook"] == [1200, 204]


def test_hostile_fact_text_cannot_break_out(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    hostile = copy.deepcopy(facts)
    hostile["project"]["org"] = "</script><script>alert(1)</script>"
    changed = copy.deepcopy(story)
    changed["chapters"][0]["blocks"].append({"type": "prose", "text": "Org: {{project.org}}"})
    changed["chapters"][0]["blocks"].append(
        {
            "type": "chart",
            "chart": "line",
            "title": "{{project.org}}",
            "data": {"x": ["a"], "series": [{"name": "x", "values": [1]}]},
        }
    )
    html = render(changed, hostile, MANIFEST, assets).fragment
    assert "<script>alert(1)" not in html
    assert "&lt;/script&gt;&lt;script&gt;alert(1)" in html
    assert "\\u003c/script\\u003e\\u003cscript\\u003ealert(1)" in html


def test_theme_words_reach_the_html_and_the_runtime(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    story = copy.deepcopy(story)
    story["theme"]["words"] = {"sources": "Shipping manifest", "show_numbers": "Open the slip"}
    page = render(story, facts, MANIFEST, assets).fragment
    assert ">Shipping manifest</h2>" in page
    assert ">Open the slip</button>" in page
    assert "Show the numbers" not in page
    assert payload(page)["words"]["sources"] == "Shipping manifest"


def test_a_widget_used_twice_ships_its_style_once(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    story = copy.deepcopy(story)
    widget = {"type": "widget", "name": "dial", "script": "w/dial.js", "style": "w/dial.css"}
    story["chapters"][0]["blocks"] += [widget, {**widget, "data": {"n": 2}}]
    files = {**assets.files, "w/dial.js": "root.textContent = 'x';", "w/dial.css": ".w-dial{}"}
    page = render(story, facts, MANIFEST, Assets(assets.css, assets.js, assets.fonts, files))
    assert page.fragment.count(".w-dial{}") == 1
    assert page.fragment.count('["dial"] = function') == 1
