"""The story format: what a story.json may contain, and the checks run before rendering."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.story.facts import REF, TOKEN, FactError, lookup, unsourced_numbers

SCHEMA_VERSION = 1

BLOCKS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "prose": (("text",), ("dropcap", "lead")),
    "stats": (("items",), ("title",)),
    "lesson": (("text",), ("title", "art")),
    "quote": (("text",), ("who", "role")),
    "chart": (
        ("chart", "data"),
        (
            "title",
            "subtitle",
            "notes",
            "source",
            "format",
            "height",
            "wide",
            "target",
            "caption",
            "y_min",
            "y_max",
            "normalize",
            "stacked",
            "horizontal",
            "unit",
            "better",
            "table",
        ),
    ),
    "scrolly": (("chart", "steps"), ("title", "subtitle", "source")),
    "timeline": (("events",), ("eras", "title", "subtitle", "source", "today")),
    "stepper": (("steps",), ("title", "subtitle", "chart", "source")),
    "compare": (("items",), ("title", "subtitle", "labels")),
    "matrix": (("items",), ("title", "subtitle", "source")),
    "roadmap": (("items",), ("title", "subtitle", "lanes", "start", "end", "today", "source")),
    "team": (("squads",), ("title", "subtitle", "services", "source")),
    "model": (("kind",), ("title", "subtitle", "inputs", "data", "source", "text")),
    "table": (("columns", "rows"), ("title", "subtitle", "source", "caption")),
    "plate": (("art",), ("caption", "spots", "width")),
}

CHARTS = ("line", "area", "stacked", "bars", "burnup", "calendar", "multiples", "slope", "waffle")
MODELS = ("forecast", "savings")
TEXT_FIELDS = ("text", "title", "subtitle", "caption", "dek", "label", "who", "role")


@dataclass
class Report:
    """Problems found in a story: errors stop the build, warnings do not."""

    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def check(story: Mapping[str, Any], facts: Mapping[str, Any]) -> Report:
    """Validate structure, every fact token and reference, and flag unsourced numbers."""
    report = Report()
    if story.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        report.errors.append(f"schema_version must be {SCHEMA_VERSION}")
    meta = story.get("meta")
    if not isinstance(meta, Mapping) or not meta.get("title"):
        report.errors.append("meta.title is required")
    sources = {str(s.get("id")) for s in story.get("sources", []) if isinstance(s, Mapping)}
    art = story.get("art", {})
    if not isinstance(art, Mapping):
        report.errors.append("art must be an object of named scenes")
        art = {}
    hero = story.get("hero", {})
    if isinstance(hero, Mapping) and hero.get("art") and hero["art"] not in art:
        report.errors.append(f"hero.art {hero['art']!r} is not defined in art")
    chapters = story.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        report.errors.append("chapters must be a non-empty list")
        chapters = []
    seen_ids: set[str] = set()
    for i, chapter in enumerate(chapters):
        where = f"chapters[{i}]"
        if not isinstance(chapter, Mapping):
            report.errors.append(f"{where} must be an object")
            continue
        cid = str(chapter.get("id", ""))
        if not cid or not cid.replace("-", "").isalnum():
            report.errors.append(f"{where}.id must be letters, digits and dashes")
        elif cid in seen_ids:
            report.errors.append(f"{where}.id {cid!r} is used twice")
        seen_ids.add(cid)
        if not chapter.get("title"):
            report.errors.append(f"{where}.title is required")
        if chapter.get("art") and chapter["art"] not in art:
            report.errors.append(f"{where}.art {chapter['art']!r} is not defined in art")
        for j, block in enumerate(chapter.get("blocks", [])):
            _check_block(block, f"{where}.blocks[{j}]", art, report)
    _walk(story, "story", facts, sources, report)
    return report


def _check_block(block: Any, where: str, art: Mapping[str, Any], report: Report) -> None:
    if not isinstance(block, Mapping) or "type" not in block:
        report.errors.append(f"{where} needs a type: {', '.join(BLOCKS)}")
        return
    kind = str(block["type"])
    if kind not in BLOCKS:
        report.errors.append(f"{where}.type {kind!r} is unknown; use one of {', '.join(BLOCKS)}")
        return
    required, optional = BLOCKS[kind]
    for key in required:
        if key not in block:
            report.errors.append(f"{where} ({kind}) is missing {key!r}")
    extra = set(block) - set(required) - set(optional) - {"type", "id"}
    if extra:
        report.warnings.append(f"{where} ({kind}) ignores {', '.join(sorted(extra))}")
    if kind == "chart" and block.get("chart") not in CHARTS:
        report.errors.append(f"{where}.chart must be one of {', '.join(CHARTS)}")
    if kind == "scrolly":
        chart = block.get("chart")
        if not isinstance(chart, Mapping) or chart.get("chart") not in CHARTS:
            report.errors.append(f"{where}.chart must be a chart spec with chart: one of {CHARTS}")
    if kind == "model" and block.get("kind") not in MODELS:
        report.errors.append(f"{where}.kind must be one of {', '.join(MODELS)}")
    if kind in ("plate", "lesson") and block.get("art") and block["art"] not in art:
        report.errors.append(f"{where}.art {block['art']!r} is not defined in art")


def _walk(
    node: Any, where: str, facts: Mapping[str, Any], sources: set[str], report: Report
) -> None:
    if isinstance(node, Mapping):
        src = node.get("source")
        if isinstance(src, str) and src and sources and src not in sources and where != "story":
            report.warnings.append(f"{where}.source {src!r} is not in sources")
        for key, value in node.items():
            if key in ("art", "facts", "sources") and where == "story":
                continue
            child = f"{where}.{key}"
            if isinstance(value, str):
                _check_text(value, child, key, facts, report)
            else:
                _walk(value, child, facts, sources, report)
    elif isinstance(node, list):
        for i, value in enumerate(node):
            child = f"{where}[{i}]"
            if isinstance(value, str):
                _check_text(value, child, "", facts, report)
            else:
                _walk(value, child, facts, sources, report)


def _check_text(text: str, where: str, key: str, facts: Mapping[str, Any], report: Report) -> None:
    if REF.match(text):
        try:
            lookup(facts, text[1:])
        except FactError as exc:
            report.errors.append(f"{where}: {exc}")
        return
    for match in TOKEN.finditer(text):
        try:
            lookup(facts, match.group(1))
        except FactError as exc:
            report.errors.append(f"{where}: {exc}")
    if key in TEXT_FIELDS:
        for number in unsourced_numbers(text):
            report.warnings.append(f"{where}: number {number!r} has no fact token")
