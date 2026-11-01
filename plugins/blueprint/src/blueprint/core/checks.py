"""blueprint's checks: architecture blocks name parts their animation holds, and prototype
links open screens that exist."""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from chronicle_engine.core.motion.embed import check_built
from chronicle_engine.core.story.model import Report

from blueprint.core.architecture import has_part


def _blocks(story: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    for i, chapter in enumerate(story.get("chapters", [])):
        for j, block in enumerate(chapter.get("blocks", [])):
            if isinstance(block, Mapping):
                yield f"chapters[{i}].blocks[{j}]", block


def architecture(story: Mapping[str, Any], files: Mapping[str, str], report: Report) -> None:
    """Every part and pin names a part the built animation holds."""
    for where, block in _blocks(story):
        if block.get("type") != "architecture":
            continue
        svg = files.get(str(block.get("svg", "")), "")
        problems = check_built(svg)
        for problem in problems:
            report.errors.append(f"{where}.svg {block.get('svg')}: {problem}")
        if problems:
            continue
        for part in dict(block.get("parts") or {}):
            if not has_part(svg, str(part)):
                report.errors.append(f"{where}.parts.{part} is not a part of {block['svg']}")
        for k, pin in enumerate(block.get("pins") or []):
            if not has_part(svg, str(pin.get("part", ""))):
                report.errors.append(f"{where}.pins[{k}].part {pin.get('part')!r} is not a part")


def links(story: Mapping[str, Any], report: Report) -> None:
    """A card or list row's link names a screen, that is a chapter id."""
    screens = {str(c.get("id")) for c in story.get("chapters", [])}
    for where, block in _blocks(story):
        if block.get("type") in ("cards", "list"):
            for k, item in enumerate(block.get("items", [])):
                link = item.get("link") if isinstance(item, Mapping) else None
                if link and str(link) not in screens:
                    report.errors.append(f"{where}.items[{k}].link {link!r} names no screen")
