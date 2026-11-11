"""KPI tiles: value, target, change and sparkline, with a status set by rule in code.

A tile meets its target when its value is on the `better` side of it; within `warn`
percent on the wrong side it is near; further off it is off target. The tile says its
status in words, so color is never the only signal.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.facts import FactError, format_value, lookup
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

REQUIRED = ("items",)
OPTIONAL = ("title", "subtitle", "source")
ITEM_KEYS = ("label", "value", "target", "better", "warn", "change", "spark", "format", "note")
WORDS = {"good": "On target", "warn": "Near target", "bad": "Off target", "none": "No target"}


def number(facts: Mapping[str, Any], ref: Any) -> float | None:
    """A ref (`@path`) or a literal as a number, or None when it is neither."""
    value = lookup(facts, str(ref)[1:]).value if str(ref).startswith("@") else ref
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def status(value: float | None, target: float | None, better: str, warn: float) -> str:
    """good, warn, bad, or none when there is no target to judge against."""
    if value is None or target is None or better not in ("up", "down"):
        return "none"
    met = value >= target if better == "up" else value <= target
    if met:
        return "good"
    gap = abs(value - target) / abs(target) * 100 if target else float("inf")
    return "warn" if gap <= warn else "bad"


def _shown(b: Builder, ref: Any, fmt: str, unit: str) -> str:
    """A ref as a fact chip with its source on hover; a literal formatted in the value's unit."""
    if str(ref).startswith("@"):
        return b.fact(str(ref)[1:], fmt)
    return tag("span", plain(format_value(ref, unit, fmt)), class_="fact")


def _tile(b: Builder, k: int, item: Mapping[str, Any], sparks: dict[str, Any]) -> str:
    fmt = str(item.get("format", "auto"))
    ref = str(item.get("value", ""))
    found = lookup(b.facts, ref[1:]) if ref.startswith("@") else None
    unit = found.unit if found else ""
    stale = (
        tag("p", f"Not refreshed since {format_value(found.as_of, '', 'date')}", class_="kpi-stale")
        if found and found.stale
        else ""
    )
    state = status(
        number(b.facts, ref),
        number(b.facts, item["target"]) if "target" in item else None,
        str(item.get("better", "")),
        float(item.get("warn", 10)),
    )
    target = (
        tag("p", "Target " + _shown(b, item["target"], fmt, unit), class_="kpi-target")
        if "target" in item
        else ""
    )
    change = (
        tag("p", _shown(b, item["change"], "auto", ""), class_="stat-delta")
        if item.get("change")
        else ""
    )
    spark = ""
    if item.get("spark"):
        sparks[str(k)] = b.plain_text(lookup(b.facts, str(item["spark"])[1:]).value)
        spark = tag("svg", class_="spark", aria_hidden="true")
    word = tag("span", class_="kpi-dot", aria_hidden="true") + WORDS[state]
    return tag(
        "div",
        tag("p", b.inline(item.get("label", "")), class_="stat-label")
        + tag("p", _shown(b, ref, fmt, unit), class_="stat-value")
        + target
        + tag("p", word, class_="kpi-status")
        + change
        + spark
        + (tag("p", b.inline(item["note"]), class_="kpi-note") if item.get("note") else "")
        + stale,
        class_=f"stat kpi kpi-{state}",
        data_i=k,
    )


def columns(count: int) -> int:
    """Tiles per row: rows of three or four, so no row is left with a single tile."""
    if count <= 2:
        return max(count, 1)
    return 4 if count % 4 == 0 or count == 7 else 3


def kpi(b: Builder, block: Mapping[str, Any]) -> str:
    """A row of KPI tiles; the sparklines draw in the page script."""
    sparks: dict[str, Any] = {}
    try:
        tiles = "".join(_tile(b, k, item, sparks) for k, item in enumerate(block["items"]))
    except (KeyError, TypeError) as exc:
        raise FactError(f"kpi item is missing {exc}") from exc
    fid = b.register({"type": "kpi", "sparks": sparks})
    title = tag("h3", b.inline(block["title"]), class_="stats-title") if block.get("title") else ""
    sub = tag("p", b.inline(block["subtitle"]), class_="stats-sub") if block.get("subtitle") else ""
    return tag(
        "div",
        title
        + sub
        + tag("div", tiles, class_=f"stats kpis cols-{columns(len(block['items']))}")
        + b.source_line(block, table=False),
        class_="stats-wrap kpi-wrap wide",
        data_fig=fid,
    )
