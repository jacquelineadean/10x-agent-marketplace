"""briefing's checks: every KPI has a target and a query, slides hold what fits, and
facts are fresh. Errors stop the build; warnings say what to fix before publishing.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from datetime import date
from typing import Any

from chronicle_engine.core.story.facts import TOKEN, FactError, lookup
from chronicle_engine.core.story.model import Report, check_text

from briefing.core import animation, slices
from briefing.core.kpi import ITEM_KEYS

SLIDE_WORDS = 60
SLIDE_BLOCKS = 4
TITLE_CHARS = 80
STALE_DAYS = 7
TEXT_KEYS = ("text", "caption", "subtitle", "dek", "note")


def _blocks(story: Mapping[str, Any]) -> Iterator[tuple[str, int, Mapping[str, Any]]]:
    for i, chapter in enumerate(story.get("chapters", [])):
        for j, block in enumerate(chapter.get("blocks", [])):
            if isinstance(block, Mapping):
                yield f"chapters[{i}].blocks[{j}]", i, block


def _expanded(story: Mapping[str, Any]) -> Iterator[tuple[str, Mapping[str, Any]]]:
    """Each block as it renders: a sliced block once per option of its filter."""
    found = slices.filters_of(story)
    for where, _, block in _blocks(story):
        key = block.get("slice")
        if key and str(key) in found:
            for option, copy in slices.variants(block, found[str(key)]):
                yield f"{where} ({key}={option})", copy
        else:
            yield where, block


def kpis(story: Mapping[str, Any], facts: Mapping[str, Any], report: Report) -> None:
    """A KPI needs a numeric value, a target, a direction, and a query behind its value."""
    for where, block in _expanded(story):
        if block.get("type") != "kpi":
            continue
        for k, item in enumerate(block.get("items", [])):
            at = f"{where}.items[{k}]"
            label = str(item.get("label", at)) if isinstance(item, Mapping) else at
            if not isinstance(item, Mapping):
                report.errors.append(f"{at} must be an object")
                continue
            for key in item:
                if key not in ITEM_KEYS:
                    report.warnings.append(f"{at} ignores {key}")
            if "target" not in item:
                report.errors.append(f"KPI {label!r} needs a target, a number or a fact")
            if item.get("better") not in ("up", "down"):
                report.errors.append(f"KPI {label!r} needs better: up or down")
            ref = str(item.get("value", ""))
            if not ref.startswith("@"):
                report.errors.append(f"KPI {label!r}: value must be a fact reference, @path")
                continue
            try:
                found = lookup(facts, ref[1:])
            except FactError as exc:
                report.errors.append(f"{at}.value: {exc}")
                continue
            if isinstance(found.value, bool) or not isinstance(found.value, int | float):
                report.errors.append(f"KPI {label!r}: {ref} must be a number")
            if not found.query:
                report.warnings.append(
                    f"KPI {label!r}: no query behind {ref}; gather it with sources or say "
                    "where it came from in its note"
                )


def sliced(story: Mapping[str, Any], facts: Mapping[str, Any], report: Report) -> None:
    """A sliced block names a defined filter, and every copy's tokens name facts."""
    found = slices.filters_of(story)
    for where, _, block in _blocks(story):
        key = block.get("slice")
        if not key:
            continue
        if str(key) not in found:
            report.errors.append(
                f"{where}.slice {key!r} names no filter; define it in a filters block"
            )
            continue
        for option, copy in slices.variants(block, found[str(key)]):
            _texts(copy, f"{where} ({key}={option})", facts, report)


def _texts(node: Any, where: str, facts: Mapping[str, Any], report: Report) -> None:
    if isinstance(node, str):
        check_text(node, where, where.rsplit(".", 1)[-1], facts, report)
    elif isinstance(node, Mapping):
        for k, v in node.items():
            _texts(v, f"{where}.{k}", facts, report)
    elif isinstance(node, list):
        for k, v in enumerate(node):
            _texts(v, f"{where}[{k}]", facts, report)


def _words(text: str) -> int:
    return len(TOKEN.sub("x", text).split())


def slides(story: Mapping[str, Any], report: Report) -> None:
    """A deck's slides keep to what a slide holds and to blocks that work without scrolling."""
    if story.get("layout") != "deck":
        return
    for i, chapter in enumerate(story.get("chapters", [])):
        name = f"slide {i + 2} ({chapter.get('id', i)})"
        title = re.sub(r"\*\*", "", str(chapter.get("title", "")))
        if len(title) > TITLE_CHARS:
            report.warnings.append(
                f"{name}: title runs {len(title)} characters; keep it under {TITLE_CHARS}"
            )
        blocks = [b for b in chapter.get("blocks", []) if isinstance(b, Mapping)]
        if len(blocks) > SLIDE_BLOCKS:
            report.warnings.append(
                f"{name}: {len(blocks)} blocks; a slide holds {SLIDE_BLOCKS} at most"
            )
        words = sum(_words(str(b.get(k, ""))) for b in blocks for k in TEXT_KEYS)
        if words > SLIDE_WORDS:
            report.warnings.append(f"{name}: {words} words; a slide holds about {SLIDE_WORDS}")
        for block in blocks:
            if block.get("type") == "scrolly":
                report.warnings.append(f"{name}: scrolly needs a scrolling page; use a stepper")


def stale(entries: Mapping[str, Any], today: date, report: Report) -> None:
    """One warning per system whose newest query is older than a week."""
    newest: dict[str, date] = {}
    for entry in entries.values():
        if not isinstance(entry, Mapping):
            continue
        try:
            when = date.fromisoformat(str(entry.get("as_of", "")))
        except ValueError:
            continue
        system = str(entry.get("system", "facts"))
        newest[system] = max(when, newest.get(system, when))
    for system, when in sorted(newest.items()):
        age = (today - when).days
        if age > STALE_DAYS:
            report.warnings.append(
                f"{system} facts are as of {when.isoformat()}, {age} days old; gather them again"
            )


def animations(story: Mapping[str, Any], files: Mapping[str, str], report: Report) -> None:
    for where, _, block in _blocks(story):
        if block.get("type") == "animation":
            for problem in animation.lint(files.get(str(block.get("svg", "")), "")):
                report.errors.append(f"{where}.svg {block.get('svg')}: {problem}")
