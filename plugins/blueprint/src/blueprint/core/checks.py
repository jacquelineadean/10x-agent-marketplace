"""blueprint's checks: architecture blocks name parts their animation holds, prototype
links open screens that exist, and a solutions file computes and matches its stored results."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.motion.embed import check_built
from chronicle_engine.core.story.model import Report, blocks_of

from blueprint.core.architecture import has_part
from blueprint.core.solutions import digest, simulate


def architecture(story: Mapping[str, Any], files: Mapping[str, str], report: Report) -> None:
    """Every part and pin names a part the built animation holds."""
    for where, block in blocks_of(story):
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
    for where, block in blocks_of(story):
        if block.get("type") in ("cards", "list"):
            for k, item in enumerate(block.get("items", [])):
                link = item.get("link") if isinstance(item, Mapping) else None
                if link and str(link) not in screens:
                    report.errors.append(f"{where}.items[{k}].link {link!r} names no screen")


def solutions(
    story: Mapping[str, Any], facts: Mapping[str, Any], files: Mapping[str, str], report: Report
) -> None:
    """The solutions file reads, every formula computes, and stored results are current."""
    blocks = list(blocks_of(story, "solutions"))
    if len(blocks) > 1:
        report.errors.append("a story holds one solutions block; start a second run for another")
    for where, block in blocks[:1]:
        path = str(block.get("file", ""))
        found = simulate.run(files.get(path, ""), facts, report)
        key = digest.fact_key(path)
        if found is not None and key in facts and digest.stale(facts[key], found):
            report.errors.append(
                f"{where}: the results under {key!r} are older than {path}; "
                "run `solutions simulate` again"
            )
