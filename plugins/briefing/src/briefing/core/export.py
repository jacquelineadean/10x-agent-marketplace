"""Deck and dashboard content as plain data, for claude.ai's Slides and Dashboard types.

Facts are filled in and formatted by code, so Claude copies text and numbers into the
type's files without doing any arithmetic. Slide images come from `briefing slides --png`.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.facts import fill, format_value, lookup

from briefing.core import kpi as kpi_block
from briefing.core import slices
from briefing.core.dashboard import as_of

TEXT = ("prose", "quote", "lesson")


def _plain(text: Any, facts: Mapping[str, Any]) -> str:
    return fill(str(text), facts).replace("**", "") if text else ""


def _tiles(block: Mapping[str, Any], facts: Mapping[str, Any]) -> list[dict[str, Any]]:
    out = []
    for item in block.get("items", []):
        ref = str(item.get("value", ""))
        found = lookup(facts, ref[1:])
        target = item.get("target")
        value = kpi_block.number(facts, ref)
        goal = kpi_block.number(facts, target) if target is not None else None
        state = kpi_block.status(
            value, goal, str(item.get("better", "")), float(item.get("warn", 10))
        )
        out.append(
            {
                "label": _plain(item.get("label", ""), facts),
                "value": format_value(found.value, found.unit, str(item.get("format", "auto"))),
                "target": format_value(goal, found.unit) if goal is not None else "",
                "status": kpi_block.WORDS[state],
                "source": found.source,
                "query": found.query,
            }
        )
    return out


def _content(
    blocks: list[Any], facts: Mapping[str, Any], story: Mapping[str, Any]
) -> dict[str, Any]:
    found = slices.filters_of(story)
    text: list[str] = []
    tiles: list[dict[str, Any]] = []
    figures: list[dict[str, str]] = []
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        key = block.get("slice")
        copies = (
            [copy for _, copy in slices.variants(block, found[str(key)])][:1]
            if key and str(key) in found
            else [block]
        )
        for copy in copies:
            kind = copy.get("type")
            if kind in TEXT:
                text.append(_plain(copy.get("text", ""), facts))
            elif kind == "kpi":
                tiles.extend(_tiles(copy, facts))
            elif kind not in ("filters",):
                figures.append({"type": str(kind), "title": _plain(copy.get("title", ""), facts)})
    return {"text": text, "kpis": tiles, "figures": figures}


def slides(story: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    """One entry per slide in deck order, the cover first and the sources last."""
    meta = story["meta"]
    chapters = story["chapters"]
    count = len(chapters) + 2
    out = [
        {
            "n": 1,
            "kind": "cover",
            "title": _plain(meta["title"], facts),
            "kicker": _plain(meta.get("kicker", ""), facts),
            "text": [_plain(meta.get("dek", ""), facts)],
            "image": "slides/slide-01.png",
        }
    ]
    for i, chapter in enumerate(chapters, start=2):
        out.append(
            {
                "n": i,
                "kind": "content",
                "title": _plain(chapter["title"], facts),
                "kicker": _plain(chapter.get("kicker", ""), facts),
                "dek": _plain(chapter.get("dek", ""), facts),
                **_content(chapter.get("blocks", []), facts, story),
                "notes": _plain(chapter.get("notes", ""), facts),
                "image": f"slides/slide-{i:02d}.png",
            }
        )
    out.append(
        {
            "n": count,
            "kind": "sources",
            "title": "Sources",
            "text": [
                f"{s.get('label', s.get('id'))}: {s.get('detail', '')}".strip(": ")
                for s in story.get("sources", [])
            ],
            "image": f"slides/slide-{count:02d}.png",
        }
    )
    return {"title": _plain(meta["title"], facts), "slides": out}


def dashboard(story: Mapping[str, Any], facts: Mapping[str, Any]) -> dict[str, Any]:
    """Each section's tiles, figures and text, with the as-of date and the sources."""
    meta = story["meta"]
    return {
        "title": _plain(meta["title"], facts),
        "dek": _plain(meta.get("dek", ""), facts),
        "as_of": as_of(story),
        "sections": [
            {"title": _plain(ch["title"], facts), **_content(ch.get("blocks", []), facts, story)}
            for ch in story["chapters"]
        ],
        "sources": [
            {
                "id": str(s.get("id", "")),
                "label": str(s.get("label", "")),
                "as_of": str(s.get("as_of", "")),
            }
            for s in story.get("sources", [])
        ],
    }
