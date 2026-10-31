"""The animation block: an animation's SVG, built by blueprint or chronicle, played in a deck.

The SVG keeps its own keyframes and theme. Its root carries `data-steps`, the start of
each step, so the deck plays one step per click by seeking the one clock.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.render import Builder

REQUIRED = ("svg",)
OPTIONAL = ("title", "subtitle", "caption", "source", "alt")
# What a built animation never holds; a file with any of these is not one of ours.
REFUSED = re.compile(r"<script|<foreignObject|\son[a-z]+\s*=|javascript:", re.I)


def lint(svg: str) -> list[str]:
    """Problems that keep an SVG file out of a page."""
    problems = []
    if not svg.lstrip().startswith("<svg"):
        problems.append("must be an animation SVG file built by `animate build`")
    if REFUSED.search(svg):
        problems.append("holds a script, an event handler or foreign markup")
    if "data-steps=" not in svg:
        problems.append("has no data-steps; rebuild it with a current `animate build`")
    return problems


def animation(b: Builder, block: Mapping[str, Any]) -> str:
    svg = str(b.files.get(str(block["svg"]), ""))
    fid = b.register({"type": "animation"})
    caption = tag("figcaption", b.inline(block["caption"])) if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + tag(
            "div", svg, class_="anim-svg", role="img", aria_label=str(block.get("alt", "")) or None
        )
        + caption
        + b.source_line(block, table=False),
        class_="fig anim",
        data_fig=fid,
    )
