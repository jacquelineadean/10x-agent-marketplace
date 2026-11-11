"""The deck layout: fixed 16:9 slides on a horizontal track.

A cover slide comes from `meta`, one slide from each chapter, and a sources slide ends
the deck. A chapter's `columns` sets its grid; a block with `"build": true` appears on a
later click; `notes` become speaker notes. The page script handles arrows, swipes, the
counter, the overview grid, the notes and one animation step per click.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

from briefing.core import slices

SKELETON: list[dict[str, Any]] = [
    {
        "id": "decision",
        "title": "State the decision this deck asks for",
        "notes": "What to say on this slide.",
        "blocks": [{"type": "prose", "text": "One line on why it matters now."}],
    },
    {
        "id": "numbers",
        "title": "The numbers behind it",
        "columns": 2,
        "blocks": [{"type": "prose", "text": "Point at the KPI or chart that proves it."}],
    },
]


def _block(b: Builder, block: Mapping[str, Any], found: Mapping[str, Any]) -> str:
    html = slices.render(b, block, found)
    return tag("div", html, class_="build", data_build=True) if block.get("build") else html


def _cover(b: Builder, count: int) -> str:
    meta = b.story["meta"]
    byline = "".join(tag("span", b.inline(x)) for x in meta.get("byline", []))
    body = (
        tag("p", b.inline(meta.get("kicker", "")), class_="kicker")
        + tag("h1", b.inline(meta["title"]))
        + tag("p", b.inline(meta.get("dek", "")), class_="dek")
        + tag("p", byline, class_="byline")
    )
    return tag(
        "section",
        tag("div", tag("div", body, class_="cover-in"), class_="slide-in"),
        class_="slide slide-cover",
        id="cover",
        data_slide=0,
        aria_label=f"1 of {count}",
    )


def _slide(b: Builder, i: int, chapter: Mapping[str, Any], count: int, found: Any) -> str:
    head = tag("p", b.inline(chapter.get("kicker", "")), class_="kicker") + tag(
        "h2", b.inline(chapter["title"])
    )
    if chapter.get("dek"):
        head += tag("p", b.inline(chapter["dek"]), class_="slide-dek")
    columns = int(chapter.get("columns", 1))
    body = "".join(_block(b, block, found) for block in chapter.get("blocks", []))
    notes = (
        tag("aside", b.paras(chapter["notes"]), class_="slide-notes")
        if chapter.get("notes")
        else ""
    )
    inner = (
        tag("header", head, class_="slide-head")
        + tag("div", body, class_=f"slide-body cols-{columns}")
        + notes
    )
    return tag(
        "section",
        tag("div", inner, class_="slide-in"),
        class_="slide",
        id=str(chapter["id"]),
        data_slide=i,
        aria_label=f"{i + 1} of {count}",
    )


def render(b: Builder, title: str) -> str:
    chapters = b.story["chapters"]
    count = len(chapters) + 2
    found = slices.filters_of(b.story)
    slides = _cover(b, count)
    for i, chapter in enumerate(chapters, start=1):
        slides += _slide(b, i, chapter, count, found)
    slides += tag(
        "section",
        tag("div", b.sources_footer(), class_="slide-in"),
        class_="slide slide-sources",
        id="sources-slide",
        data_slide=count - 1,
        aria_label=f"{count} of {count}",
    )
    words = b.theme.words
    bar = (
        tag("button", "&#8592;", type="button", class_="deck-prev", aria_label=plain(words["back"]))
        + tag("p", f"1 / {count}", class_="deck-count", aria_live="polite")
        + tag(
            "button", "&#8594;", type="button", class_="deck-next", aria_label=plain(words["next"])
        )
        + tag(
            "button",
            plain(words["overview"]),
            type="button",
            class_="deck-grid",
            aria_pressed="false",
        )
        + tag("button", "Notes", type="button", class_="deck-notes", aria_pressed="false")
        + tag("button", type="button", class_="theme-btn", aria_label="Switch light or dark theme")
    )
    return tag(
        "main",
        tag("div", slides, class_="deck-track"),
        class_="deck",
        id="top",
        aria_label=title,
        aria_roledescription="slide deck",
    ) + tag("nav", bar, class_="deck-bar", aria_label="Slides")
