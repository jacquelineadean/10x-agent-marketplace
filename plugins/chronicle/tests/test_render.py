from __future__ import annotations

import copy
import json
import re
from typing import Any

from chronicle.core.story.render import Assets, render

ASSETS = Assets(css="/* css */", js="/* js */")
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
    story: dict[str, Any], facts: dict[str, Any]
) -> None:
    page = render(story, facts, MANIFEST, ASSETS)
    assert "{{" not in page.fragment
    assert '<span class="fact" tabindex="0" data-src="datadog"' in page.fragment
    assert page.fragment.startswith("<title>Keystone</title>")
    assert page.document.startswith("<!doctype html>")
    assert page.art_files == ["art/hero--keystone.webp", "art/hero.webp"]


def test_figure_specs_carry_resolved_data(story: dict[str, Any], facts: dict[str, Any]) -> None:
    data = payload(render(story, facts, MANIFEST, ASSETS).fragment)
    charts = [f for f in data["figs"].values() if f.get("chart") == "burnup"]
    assert charts[0]["data"]["done"] == facts["plan"]["done"]
    assert [n["no"] for n in data["nav"]] == ["I", "II", "III", "IV", "V", "VI", "VII"]
    plate = next(f for f in data["figs"].values() if f.get("type") == "plate")
    assert plate["anchors"]["hook"] == [1200, 204]


def test_hostile_fact_text_cannot_break_out(story: dict[str, Any], facts: dict[str, Any]) -> None:
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
    html = render(changed, hostile, MANIFEST, ASSETS).fragment
    assert "<script>alert(1)" not in html
    assert "&lt;/script&gt;&lt;script&gt;alert(1)" in html
    assert "\\u003c/script\\u003e\\u003cscript\\u003ealert(1)" in html
