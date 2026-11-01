"""The architecture block: a built animation with part details, pins and a step player.

The block shows an animation's SVG (a TAD, a sequence, an ERD or a drawn diagram). Each part
named in `parts` opens its details when clicked; each pin marks a decision or a question on
a part; the player steps through the animation's own steps by seeking its one clock.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.render import Builder

REQUIRED = ("svg",)
OPTIONAL = ("title", "subtitle", "caption", "source", "alt", "parts", "pins", "player")
SLUG = re.compile(r'class="chr-a chr-a-([a-z0-9-]+)"')
# A part's own element in a built animation: TAD nodes, groups and edges, drawn ids.
PREFIXES = ("n", "g", "e", "d")


def slug_of(svg: str) -> str:
    found = SLUG.search(svg)
    return found.group(1) if found else ""


def has_part(svg: str, part: str) -> bool:
    """Whether the built SVG holds the part, under any of the kinds' id prefixes."""
    slug = slug_of(svg)
    return any(f'id="{slug}-{prefix}-{part}"' in svg for prefix in PREFIXES)


def architecture(b: Builder, block: Mapping[str, Any]) -> str:
    svg = str(b.files.get(str(block["svg"]), ""))
    parts = {
        str(pid): {
            "title": b.plain_text(str(p.get("title", pid))),
            "text": b.plain_text(str(p.get("text", ""))),
        }
        for pid, p in dict(block.get("parts") or {}).items()
        if isinstance(p, Mapping)
    }
    pins = [
        {
            "part": str(p.get("part", "")),
            "title": b.plain_text(str(p.get("title", ""))),
            "text": b.plain_text(str(p.get("text", ""))),
        }
        for p in block.get("pins") or []
        if isinstance(p, Mapping)
    ]
    fid = b.register(
        {"type": "architecture", "parts": parts, "pins": pins, "player": block.get("player", True)}
    )
    listing = "".join(
        tag("dt", b.inline(p.get("title", pid))) + tag("dd", b.inline(p.get("text", "")))
        for pid, p in dict(block.get("parts") or {}).items()
        if isinstance(p, Mapping)
    ) + "".join(
        tag("dt", f"Pin {k + 1}: " + b.inline(p.get("title", "")))
        + tag("dd", b.inline(p.get("text", "")))
        for k, p in enumerate(block.get("pins") or [])
        if isinstance(p, Mapping)
    )
    hint = tag("p", "Select a part or a pin for its details.", class_="arch-hint")
    caption = tag("figcaption", b.inline(block["caption"])) if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + tag(
            "div",
            tag(
                "div",
                svg,
                class_="arch-svg",
                role="img",
                aria_label=str(block.get("alt", "")) or None,
            )
            + tag("div", class_="arch-pins"),
            class_="arch-stage",
        )
        + tag("div", class_="arch-player")
        + tag("aside", hint, class_="arch-detail", aria_live="polite")
        + (
            tag(
                "details", tag("summary", "Parts and pins") + tag("dl", listing), class_="arch-list"
            )
            if listing
            else ""
        )
        + caption
        + b.source_line(block, table=False),
        class_="fig arch wide",
        data_fig=fid,
    )
