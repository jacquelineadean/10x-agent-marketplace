"""Tour: a painted map whose stops open scenes, walked by a route in the page's bar.

A `tour` block shows a painted map with a dotted route through its numbered stops and a
few info pins between them. A stop opens its scene in the same box: a plate, a `rooms`
set or a `panorama`, with an intro, a link to the chapter that tells the stop at length,
and a button to the next stop. The page's bar gains the route: one mark per stop, a
walker at the open stop, and visited stops colored; visits are remembered on the device.
Without scripts the map's stops link to the scenes, which follow the map in order.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.dispatch import render_block
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.model import blocks_of
from chronicle_engine.core.story.render import Builder

from chronicle.core.story import keys, plates

SCENES = ("plate", "rooms", "panorama")
# A stop marker past this fraction of the map's width puts its label on the left.
LABEL_FLIP = 0.7

Block = Mapping[str, Any]


def _stops(block: Block) -> list[Block]:
    return [s for s in block.get("stops", []) if isinstance(s, Mapping)]


def tour(b: Builder, block: Block) -> str:
    key = str(block["art"])
    entry = b.manifest.get(key)
    if not entry:
        return ""
    w, h = float(entry["width"]), float(entry["height"])
    anchors = entry.get("anchors", {})
    base = str(block.get("id") or f"tour-{b.counter + 1}")
    stops = _stops(block)
    points = [plates.point(s.get("at"), anchors) or (w / 2, h / 2) for s in stops]
    fid = b.register(
        {
            "type": "tour",
            "key": keys.stored(b.story, "tour", block.get("key")),
            "stops": [
                {
                    "id": str(s.get("id", "")),
                    "short": str(b.plain_text(str(s.get("short") or s.get("title", "")))),
                    "title": str(b.plain_text(str(s.get("title", "")))),
                    "at": [round(100 * x / w, 2), round(100 * y / h, 2)],
                    "chapter": str(s.get("chapter", "")),
                }
                for s, (x, y) in zip(stops, points, strict=True)
            ],
            "title": str(b.plain_text(str(block.get("title", "")))),
        }
    )
    route = " ".join(f"{'M' if i == 0 else 'L'}{x:.0f} {y:.0f}" for i, (x, y) in enumerate(points))
    marks = tag(
        "svg",
        tag("path", class_="tr-route-shadow", d=route) + tag("path", class_="tr-route", d=route),
        class_="tr-routes",
        viewBox=f"0 0 {w:.0f} {h:.0f}",
        preserveAspectRatio="none",
        aria_hidden="true",
    )
    for i, (stop, (x, y)) in enumerate(zip(stops, points, strict=True)):
        flip = " lbl-left" if x > LABEL_FLIP * w else ""
        marks += tag(
            "a",
            tag("span", str(i + 1), class_="tr-badge", aria_hidden="true")
            + tag("span", b.inline(stop.get("short") or stop.get("title", "")), class_="tr-lbl"),
            class_=f"tr-stop{flip}",
            href=f"#{base}-stop-{i}",
            data_stop=i,
            aria_label=f"Stop {i + 1}: {b.plain_text(str(stop.get('title', '')))}",
            style=f"left:{100 * x / w:.2f}%;top:{100 * y / h:.2f}%",
        )
    pins = [p for p in block.get("pins", []) if isinstance(p, Mapping)]
    listed = ""
    for k, pin in enumerate(pins):
        at = plates.point(pin.get("at"), anchors)
        if at:
            marks += tag(
                "button",
                type="button",
                class_="tr-pin",
                data_pin=k,
                aria_label=str(b.plain_text(str(pin.get("title", "")))),
                style=f"left:{100 * at[0] / w:.2f}%;top:{100 * at[1] / h:.2f}%",
            )
        listed += tag("dt", b.inline(pin.get("title", ""))) + tag(
            "dd", b.paras(pin.get("text", ""))
        )
    hub = (
        plates.plate(b, key, width="inset", extra=marks)
        + tag("div", class_="tr-pin-card", hidden=True, aria_live="polite")
        + (tag("dl", listed, class_="tr-pins") if listed else "")
        + tag(
            "p",
            tag("span", b.inline(block.get("hint", "Pick a stop to go there.")), class_="tr-hint")
            + " "
            + tag("span", class_="tr-count"),
            class_="tr-hub-foot",
        )
    )
    scenes = "".join(_scene(b, stop, i, stops, base) for i, stop in enumerate(stops))
    head = tag(
        "div",
        tag("button", "Map", type="button", class_="tr-btn tr-tomap", hidden=True)
        + tag("p", class_="tr-where", aria_live="polite")
        + tag(
            "div",
            tag("button", "‹", type="button", class_="tr-prev", aria_label="Previous stop")
            + tag("button", "›", type="button", class_="tr-next", aria_label="Next stop")
            + tag("button", "Full screen", type="button", class_="tr-btn tr-fs", hidden=True),
            class_="tr-nav",
        ),
        class_="tr-head",
    )
    app = tag(
        "div",
        head
        + tag("div", hub, class_="tr-hub", role="region", aria_label=_hub_label(b, block, stops))
        + tag("div", scenes, class_="tr-scenes"),
        class_="tr-app",
    )
    return tag(
        "figure",
        b.heading(block) + app + b.source_line(block, table=False),
        class_="fig tour wide",
        id=base,
        data_fig=fid,
    )


def _hub_label(b: Builder, block: Block, stops: list[Block]) -> str:
    title = str(b.plain_text(str(block.get("title") or "the tour")))
    return f"Map of {title} with {len(stops)} stops"


def _scene(b: Builder, stop: Block, i: int, stops: list[Block], base: str) -> str:
    sid = f"{base}-stop-{i}"
    intro = tag(
        "div",
        tag("p", f"Stop {i + 1} of {len(stops)}", class_="tr-kicker")
        + tag(
            "h3",
            b.inline(stop.get("title", "")),
            class_="tr-title",
            id=f"{sid}-title",
            tabindex="-1",
        )
        + tag("div", b.paras(stop.get("intro", "")), class_="tr-text"),
        class_="tr-intro",
    )
    scene = stop.get("scene")
    body = (
        render_block(b, scene) if isinstance(scene, Mapping) and scene.get("type") in SCENES else ""
    )
    foot = tag("a", "Back to the map", class_="tr-btn ghost tr-back", href=f"#{base}")
    if stop.get("chapter"):
        foot += tag(
            "a",
            "Read this stop in the guide ↓",
            class_="tr-btn ghost tr-read",
            href=f"#{stop['chapter']}",
        )
    if i + 1 < len(stops):
        later = stops[i + 1]
        foot += tag(
            "a",
            f"Next stop: {b.inline(later.get('short') or later.get('title', ''))} ›",
            class_="tr-btn tr-on",
            href=f"#{base}-stop-{i + 1}",
            data_stop=i + 1,
        )
    return tag(
        "section",
        intro + body + tag("div", foot, class_="tr-foot"),
        class_="tr-scene",
        id=sid,
        data_stop=i,
        aria_labelledby=f"{sid}-title",
    )


def check(story: Mapping[str, Any], anchors: Mapping[str, set[str]], report: Any) -> None:
    """The map, the stops and their scenes, the pins."""
    art = story.get("art", {}) if isinstance(story.get("art"), Mapping) else {}
    chapters = {str(c.get("id")) for c in story.get("chapters", []) if isinstance(c, Mapping)}
    for where, block in blocks_of(story, "tour"):
        _check(block, where, art, anchors, chapters, report)


def _check(
    block: Block,
    where: str,
    art: Mapping[str, Any],
    anchors: Mapping[str, set[str]],
    chapters: set[str],
    report: Any,
) -> None:
    key = str(block.get("art", ""))
    known = anchors.get(key, set())
    stops = block.get("stops")
    if not isinstance(stops, list) or not stops:
        report.errors.append(f"{where}.stops must be a non-empty list of stops")
        return
    ids = [str(s.get("id", "")) for s in stops if isinstance(s, Mapping)]
    for i, stop in enumerate(stops):
        at = f"{where}.stops[{i}]"
        if not isinstance(stop, Mapping):
            report.errors.append(f"{at} must be an object")
            continue
        sid = str(stop.get("id", ""))
        if not keys.ID.match(sid) or ids.count(sid) > 1:
            report.errors.append(f"{at}.id {sid!r} must be unique, lowercase letters and -")
        if not stop.get("title"):
            report.errors.append(f"{at}.title is required")
        plates.check_at(stop.get("at"), f"{at}.at", known, report)
        if stop.get("chapter") and str(stop["chapter"]) not in chapters:
            report.errors.append(f"{at}.chapter {stop['chapter']!r} is no chapter id")
        scene = stop.get("scene")
        if scene is None:
            continue
        if not isinstance(scene, Mapping) or scene.get("type") not in SCENES:
            report.errors.append(f"{at}.scene must be a block of type {', '.join(SCENES)}")
        elif scene.get("type") == "plate" and scene.get("art") not in art:
            report.errors.append(f"{at}.scene.art {scene.get('art')!r} is not defined in art")
    for k, pin in enumerate(block.get("pins", [])):
        if not isinstance(pin, Mapping) or not pin.get("title"):
            report.errors.append(f"{where}.pins[{k}] needs a title, at and text")
            continue
        plates.check_at(pin.get("at"), f"{where}.pins[{k}].at", known, report)
    if block.get("key") is not None and not keys.ID.match(str(block["key"])):
        report.errors.append(f"{where}.key must be lowercase letters, digits and -")
