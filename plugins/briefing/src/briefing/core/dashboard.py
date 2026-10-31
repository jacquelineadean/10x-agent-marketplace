"""The dashboard layout: a header with the as-of stamp, then sections of tiles, charts and tables.

Each chapter is a section; its blocks sit in a grid, and `"span": 2` widens a block to
two columns. The as-of stamp is the latest `as_of` among the story's sources and `meta`.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.facts import format_value
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

from briefing.core import slices

SKELETON: list[dict[str, Any]] = [
    {
        "id": "headline",
        "title": "Headline measures",
        "blocks": [
            {"type": "prose", "text": "Replace with a kpi block once the facts are gathered."}
        ],
    },
    {
        "id": "detail",
        "title": "What moved",
        "blocks": [{"type": "prose", "text": "One line per chart on what to see in it."}],
    },
]
ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Blocks that read best across the whole grid.
FULL = ("kpi", "filters", "table", "stats", "timeline", "roadmap")


def as_of(story: Mapping[str, Any]) -> str:
    """The latest ISO date among the sources' `as_of` and `meta.as_of`, or ''."""
    dates = [str(s.get("as_of", "")) for s in story.get("sources", []) if isinstance(s, Mapping)]
    dates.append(str(story.get("meta", {}).get("as_of", "")))
    found = sorted(d for d in dates if ISO.match(d))
    return found[-1] if found else ""


def _cell(b: Builder, block: Mapping[str, Any], found: Mapping[str, Any]) -> str:
    span = int(block.get("span", 2 if block.get("type") in FULL else 1))
    return tag("div", slices.render(b, block, found), class_=f"db-cell span-{min(max(span, 1), 2)}")


def render(b: Builder, title: str) -> str:
    meta = b.story["meta"]
    found = slices.filters_of(b.story)
    stamp = as_of(b.story)
    when = (
        tag("p", f"As of {plain(format_value(stamp, '', 'date'))}", class_="db-asof")
        if stamp
        else ""
    )
    head = tag(
        "div",
        tag("p", b.inline(meta.get("kicker", "")), class_="kicker")
        + tag("h1", b.inline(meta["title"]))
        + tag("p", b.inline(meta.get("dek", "")), class_="dek")
        + when,
        class_="db-title",
    ) + tag("button", type="button", class_="theme-btn", aria_label="Switch light or dark theme")
    sections = ""
    for i, chapter in enumerate(b.story["chapters"]):
        cells = "".join(_cell(b, block, found) for block in chapter.get("blocks", []))
        sections += tag(
            "section",
            tag("h2", b.inline(chapter["title"]), class_="db-h")
            + (tag("p", b.inline(chapter["dek"]), class_="db-dek") if chapter.get("dek") else "")
            + tag("div", cells, class_="db-grid"),
            class_="db-section",
            id=str(chapter["id"]),
            data_ch=i,
        )
    return tag("header", head, class_="db-head") + tag(
        "main", sections + b.sources_footer(), class_="dashboard", id="top", aria_label=title
    )
