"""Rooms: paintings with numbered details and doorways between them.

A `rooms` block walks a set of painted rooms. Each room is a plate. Numbered dots open a
detail in the caption under the painting, and doorways move to another room: the view
pushes through the door while the next room develops from gray. Tabs list the rooms.
Without scripts every room shows in turn, with its details listed and its doorways as
links to the room they open.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.render import Builder

from chronicle.core.story import plates
from chronicle.core.story.keys import ID

ARROWS = {"up": "↑", "down": "↓", "left": "←", "right": "→"}
# Doorways past these fractions of the width keep their label inside the painting.
EDGE = 0.2

Block = Mapping[str, Any]


def _rooms(block: Block) -> list[Block]:
    return [r for r in block.get("rooms", []) if isinstance(r, Mapping)]


def rooms(b: Builder, block: Block) -> str:
    """The rooms as tab panels, each a plate with its dots and doorways and a caption."""
    found = _rooms(block)
    base = str(block.get("id") or f"rooms-{b.counter + 1}")
    index = {str(r.get("id")): i for i, r in enumerate(found)}
    fid = b.register({"type": "rooms", "rooms": [str(r.get("id")) for r in found]})
    tabs = ""
    panels = ""
    for i, room in enumerate(found):
        tab_id, panel_id = f"{base}-tab-{i}", f"{base}-room-{i}"
        tabs += tag(
            "button",
            b.inline(room.get("short") or room.get("title", "")),
            type="button",
            role="tab",
            id=tab_id,
            aria_controls=panel_id,
            aria_selected="true" if i == 0 else "false",
            tabindex="0" if i == 0 else "-1",
            data_room=i,
        )
        panels += _room(b, room, i, base, index, tab_id if len(found) > 1 else "")
    tablist = (
        tag("div", tabs, class_="rm-tabs", role="tablist", aria_label="Rooms")
        if len(found) > 1
        else ""
    )
    return tag(
        "figure",
        b.heading(block)
        + tablist
        + tag("div", panels, class_="rm-stage")
        + b.source_line(block, table=False),
        class_="fig rooms wide",
        id=base,
        data_fig=fid,
    )


def _room(b: Builder, room: Block, i: int, base: str, index: Mapping[str, int], tab_id: str) -> str:
    key = str(room.get("art", ""))
    entry = b.manifest.get(key) or {}
    w, h = float(entry.get("width", 1) or 1), float(entry.get("height", 1) or 1)
    anchors = entry.get("anchors", {})
    marks = ""
    details = ""
    for k, detail in enumerate(d for d in room.get("details", []) if isinstance(d, Mapping)):
        at = plates.point(detail.get("at"), anchors)
        title = b.inline(detail.get("title", ""))
        did = f"{base}-d{i}-{k}"
        if at:
            marks += tag(
                "a",
                str(k + 1),
                class_="rm-dot",
                href=f"#{did}",
                data_k=k,
                aria_label=f"Detail {k + 1}: {b.plain_text(str(detail.get('title', '')))}",
                style=f"left:{100 * at[0] / w:.2f}%;top:{100 * at[1] / h:.2f}%",
            )
        details += tag(
            "li",
            tag("h5", title, class_="rm-detail-title", tabindex="-1")
            + tag("div", b.paras(detail.get("text", "")), class_="rm-detail-text"),
            id=did,
            data_k=k,
        )
    for door in (d for d in room.get("exits", []) if isinstance(d, Mapping)):
        at = plates.point(door.get("at"), anchors)
        to = index.get(str(door.get("to")))
        if not at or to is None:
            continue
        edge = " edge-l" if at[0] < EDGE * w else " edge-r" if at[0] > (1 - EDGE) * w else ""
        marks += tag(
            "a",
            tag("span", ARROWS.get(str(door.get("arrow", "up")), "↑"), class_="rm-arrow")
            + tag("span", b.inline(door.get("label", "")), class_="rm-exit-label"),
            class_=f"rm-exit{edge}",
            href=f"#{base}-room-{to}",
            data_to=to,
            data_at=f"{100 * at[0] / w:.1f} {100 * at[1] / h:.1f}",
            style=f"left:{100 * at[0] / w:.2f}%;top:{100 * at[1] / h:.2f}%",
        )
    painting = plates.plate(b, key, width="inset", extra=marks) if entry else ""
    hint = "Tap a numbered dot for a closer look"
    hint += ", or a doorway to walk on." if room.get("exits") else "."
    caption = tag(
        "div",
        tag("p", b.inline(room.get("kicker", "")), class_="rm-kicker")
        + tag("h4", b.inline(room.get("title", "")), class_="rm-title", tabindex="-1")
        + tag("div", b.paras(room.get("text", "")), class_="rm-text")
        + (tag("p", hint, class_="rm-hint") if details else ""),
        class_="rm-about",
    )
    listed = tag("ol", details, class_="rm-details") if details else ""
    return tag(
        "section",
        painting + tag("div", caption + listed, class_="rm-cap", aria_live="polite"),
        class_="rm-room",
        id=f"{base}-room-{i}",
        role="tabpanel" if tab_id else None,
        aria_labelledby=tab_id or None,
        data_room=i,
        data_focus=f"{float(room.get('focus', 0.5)):g}",
    )


def check(story: Mapping[str, Any], anchors: Mapping[str, set[str]], report: Any) -> None:
    """Room ids, paintings, details and doorways of every rooms block, tour stops included."""
    art = story.get("art", {}) if isinstance(story.get("art"), Mapping) else {}
    for where, block in blocks(story, "rooms"):
        check_block(block, where, art, anchors, report)


def check_block(
    block: Block, where: str, art: Mapping[str, Any], anchors: Mapping[str, set[str]], report: Any
) -> None:
    found = block.get("rooms")
    if not isinstance(found, list) or not found:
        report.errors.append(f"{where}.rooms must be a non-empty list of rooms")
        return
    ids = [str(r.get("id", "")) for r in found if isinstance(r, Mapping)]
    for i, room in enumerate(found):
        at = f"{where}.rooms[{i}]"
        if not isinstance(room, Mapping):
            report.errors.append(f"{at} must be an object")
            continue
        rid = str(room.get("id", ""))
        if not ID.match(rid) or ids.count(rid) > 1:
            report.errors.append(f"{at}.id {rid!r} must be unique, lowercase letters and -")
        key = str(room.get("art", ""))
        if key not in art:
            report.errors.append(f"{at}.art {key!r} is not defined in art")
        if not room.get("title"):
            report.errors.append(f"{at}.title is required")
        known = anchors.get(key, set())
        for k, detail in enumerate(room.get("details", [])):
            _check_point(detail, f"{at}.details[{k}]", known, report)
            if isinstance(detail, Mapping) and not detail.get("title"):
                report.errors.append(f"{at}.details[{k}].title is required")
        for k, door in enumerate(room.get("exits", [])):
            here = f"{at}.exits[{k}]"
            _check_point(door, here, known, report)
            if not isinstance(door, Mapping):
                continue
            if door.get("to") not in ids or door.get("to") == rid:
                report.errors.append(f"{here}.to must name another room of this block")
            if door.get("arrow", "up") not in ARROWS:
                report.errors.append(f"{here}.arrow must be one of {', '.join(ARROWS)}")
            if not door.get("label"):
                report.errors.append(f"{here}.label is required")


def _check_point(item: Any, where: str, known: set[str], report: Any) -> None:
    if not isinstance(item, Mapping):
        report.errors.append(f"{where} must be an object")
        return
    plates.check_at(item.get("at"), f"{where}.at", known, report)


def blocks(story: Mapping[str, Any], kind: str) -> list[tuple[str, Block]]:
    """Every block of one type in the chapters and in tour stops, with its path."""
    out: list[tuple[str, Block]] = []
    for i, chapter in enumerate(story.get("chapters", [])):
        if not isinstance(chapter, Mapping):
            continue
        for j, block in enumerate(chapter.get("blocks", [])):
            if not isinstance(block, Mapping):
                continue
            where = f"chapters[{i}].blocks[{j}]"
            if block.get("type") == kind:
                out.append((where, block))
            if block.get("type") == "tour":
                for k, stop in enumerate(block.get("stops", [])):
                    scene = stop.get("scene") if isinstance(stop, Mapping) else None
                    if isinstance(scene, Mapping) and scene.get("type") == kind:
                        out.append((f"{where}.stops[{k}].scene", scene))
    return out
