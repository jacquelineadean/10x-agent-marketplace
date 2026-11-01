"""Panorama: a wide painted habitat to drag across, with animals, zones, a tide and a journal.

A `panorama` block shows one wide painting at a fixed height; the reader drags it, uses the
arrow keys or the edge buttons to look along it. Animals are rigs painted in their own
drawings and placed by their foot point; each walks, swims, crawls, glides, leaps or hops
over its range and opens a field card when picked. Zones name stretches of the painting.
A tide slider fades a tide layer, slides a surf layer and hides the animals that only show
at one end of the tide. A journal remembers every species found, across the page.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag, void
from chronicle_engine.core.story.render import Builder

from chronicle.core.story import keys, plates
from chronicle.core.story.rooms import blocks
from chronicle.core.watercolor.svg.parse import Drawing

BEHAVIORS = ("wander", "scuttle", "swim", "crawl", "glide", "arc", "hop", "stay")
TIDES = ("low", "high")
VIEW = {"desktop": 520, "phone": 360}

Block = Mapping[str, Any]


def rig_of(manifest: Mapping[str, Any], animal: Block) -> tuple[str, dict[str, Any], list[Any]]:
    """The animal's rig: its name, its settings and its parts, from the painting it names."""
    entry = manifest.get(str(animal.get("art", ""))) or {}
    rigs = dict(entry.get("rigs", {}))
    name = str(animal.get("rig") or (next(iter(rigs)) if len(rigs) == 1 else ""))
    parts = [p for p in entry.get("layers", []) if p.get("rig") == name]
    return name, dict(rigs.get(name, {})), parts


def panorama(b: Builder, block: Block) -> str:
    key = str(block["art"])
    entry = b.manifest.get(key)
    if not entry:
        return ""
    w, h = int(entry["width"]), int(entry["height"])
    b.art_files.append(str(entry["file"]))
    tide = block.get("tide") if isinstance(block.get("tide"), Mapping) else None
    front = {str(n) for n in block.get("front", [])}
    roles = {str(tide.get("layer", "")): "tide", str(tide.get("surf", "")): "surf"} if tide else {}
    world = void(
        "img",
        class_="pa-bg",
        src=str(entry["file"]),
        alt=str(b.story.get("art", {}).get(key, {}).get("alt", "")),
        width=w,
        height=h,
        draggable="false",
    )
    for layer in entry.get("layers", []):
        if layer.get("rig"):
            continue
        b.art_files.append(str(layer["file"]))
        x, y, lw, lh = (float(v) for v in layer["box"])
        name = str(layer.get("name", ""))
        role = roles.get(name, "front" if name in front else "layer")
        world += void(
            "img",
            class_=f"pa-layer pa-l-{role}" + (" mult" if layer.get("blend") != "normal" else ""),
            src=str(layer["file"]),
            alt="",
            aria_hidden="true",
            draggable="false",
            style=f"left:{x:.0f}px;top:{y:.0f}px;width:{lw:.0f}px;height:{lh:.0f}px;"
            f"z-index:{h + 10 if role == 'front' else 1}",
        )
    animals = [a for a in block.get("animals", []) if isinstance(a, Mapping)]
    cards = []
    for animal in animals:
        world += _animal(b, animal)
        cards.append(
            {
                "id": str(animal.get("id", "")),
                "name": str(b.plain_text(str(animal.get("name", "")))),
                "latin": str(b.plain_text(str(animal.get("latin", "")))),
                "where": str(b.plain_text(str(animal.get("where", "")))),
                "fact": str(b.plain_text(str(animal.get("fact", "")))),
            }
        )
    zones = [z for z in block.get("zones", []) if isinstance(z, Mapping)]
    if zones:
        world += tag("div", class_="pa-zone-spot", aria_hidden="true")
    view = {**VIEW, **dict(block.get("view") or {})}
    spec: dict[str, Any] = {
        "type": "panorama",
        "width": w,
        "height": h,
        "view": view,
        "animals": cards,
        "zones": [
            {
                "label": str(b.plain_text(str(z.get("label", "")))),
                "from": float(z.get("from", 0)),
                "to": float(z.get("to", w)),
                "text": str(b.plain_text(str(z.get("text", "")))),
            }
            for z in zones
        ],
        "intro": str(b.plain_text(str(block.get("intro", "")))),
        "journal": _journal_key(b, block),
    }
    if tide:
        spec["tide"] = {
            "start": float(tide.get("start", 0.5)),
            "shift": [float(v) for v in tide.get("shift", [0, 0])],
            "watch": [[float(a), float(z)] for a, z in tide.get("watch", [])],
            "notes": [
                {"from": float(n.get("from", 0)), "text": str(b.plain_text(str(n.get("text", ""))))}
                for n in tide.get("notes", [])
                if isinstance(n, Mapping)
            ],
            "words": [str(tide.get(k, d)) for k, d in (("low", "Low"), ("high", "High"))],
        }
    fid = b.register(spec)
    label = str(
        b.plain_text(
            str(
                block.get("label")
                or "Painted panorama; drag it or use the arrow keys to look along it"
            )
        )
    )
    zone_bar = (
        tag(
            "div",
            "".join(
                tag("button", b.inline(z.get("label", "")), type="button", class_="pa-zone")
                for z in zones
            ),
            class_="pa-zones",
            aria_label="Places in the painting",
            role="group",
        )
        if zones
        else ""
    )
    nav = tag(
        "button", "‹", type="button", class_="pa-nav pa-nav-l", aria_label="Look left", hidden=True
    ) + tag(
        "button", "›", type="button", class_="pa-nav pa-nav-r", aria_label="Look right", hidden=True
    )
    stage = tag(
        "div",
        tag("div", world, class_="pa-world", style=f"width:{w}px;height:{h}px"),
        class_="pa-view",
        tabindex="0",
        role="region",
        aria_label=label,
        style=f"height:{float(view['desktop']):.0f}px",
    )
    tide_row = _tide_row(b, block, fid) if tide else ""
    body = (
        b.heading(block)
        + zone_bar
        + tag("div", stage + nav, class_="pa-frame")
        + tide_row
        + tag(
            "div", tag("p", b.inline(block.get("intro", "")), class_="pa-intro"), class_="pa-card"
        )
        + _fallback(b, animals, zones)
        + b.source_line(block, table=False)
    )
    return tag("figure", body, class_="fig panorama wide", id=block.get("id"), data_fig=fid)


def _animal(b: Builder, animal: Block) -> str:
    name, rig, parts = rig_of(b.manifest, animal)
    if not parts:
        return ""
    x0, y0, rw, rh = plates.rig_box(parts)
    scale = float(animal.get("scale", 1))
    foot = rig.get("foot") or [x0 + rw / 2, y0 + rh]
    fx, fy = float(foot[0]) - x0, float(foot[1]) - y0
    x, y = (float(v) for v in animal.get("at", [0, 0]))
    behavior = str(animal.get("behavior", "wander"))
    lo, hi = (float(v) for v in animal.get("range", [x, x]))
    rest = [float(v) for v in animal.get("rest", [2, 6])]
    speed = float(animal.get("speed", float(rig.get("speed", 30)) * scale))
    stride = float(animal.get("stride", float(rig.get("stride", 60)) * scale))
    inner = tag(
        "span",
        plates.rig_parts(b, parts),
        class_="rig",
        data_gait=str(rig.get("gait", "still")),
        data_bob=f"{float(rig.get('bob', 2)):g}",
        data_h=f"{rh:g}",
        data_w=f"{rw:g}",
        style=f"transform-origin:{100 * fx / rw:.1f}% {100 * fy / rh:.1f}%",
    )
    return tag(
        "button",
        inner,
        type="button",
        class_="pa-animal",
        aria_label=str(b.plain_text(str(animal.get("name", name)))),
        data_species=str(animal.get("id", "")),
        data_behavior=behavior,
        data_at=f"{x:g} {y:g}",
        data_foot=f"{fx * scale:.1f} {fy * scale:.1f}",
        data_range=f"{lo:g} {hi:g}",
        data_rest=" ".join(f"{v:g}" for v in rest[:2]),
        data_speed=f"{speed:.1f}",
        data_stride=f"{max(1.0, stride):.1f}",
        data_face=str(int(animal.get("face", 1))),
        data_tide=str(animal.get("tide", "")) or None,
        data_z=str(int(animal.get("z", 0))),
        data_offset=f"{float(animal.get('offset', 0)):g}",
        data_height=f"{float(animal.get('height', 60)):g}",
        data_period=f"{float(animal.get('period', 6.5)):g}",
        style=(
            f"left:{x - fx * scale:.1f}px;top:{y - fy * scale:.1f}px;"
            f"width:{rw * scale:.1f}px;height:{rh * scale:.1f}px;"
            f"z-index:{max(2, round(y) + int(animal.get('z', 0)))}"
        ),
    )


def _journal_key(b: Builder, block: Block) -> str:
    """Panoramas that share a key share one journal; true keys it by the page's title."""
    found = block.get("journal")
    if not found:
        return ""
    return keys.stored(b.story, "journal", None if found is True else found)


def _tide_row(b: Builder, block: Block, fid: str) -> str:
    tide = block["tide"]
    rid = f"{block.get('id') or fid}-tide"
    return tag(
        "div",
        tag("label", b.inline(tide.get("label", "Tide")), for_=rid, class_="pa-tide-label")
        + tag("span", b.inline(tide.get("low", "Low")), class_="pa-tide-end", aria_hidden="true")
        + void(
            "input",
            type="range",
            id=rid,
            class_="pa-tide-range",
            min="0",
            max="100",
            value=f"{100 * float(tide.get('start', 0.5)):.0f}",
        )
        + tag("span", b.inline(tide.get("high", "High")), class_="pa-tide-end", aria_hidden="true"),
        class_="pa-tide-row",
    ) + tag("p", class_="pa-tide-note", aria_live="polite")


def _fallback(b: Builder, animals: list[Block], zones: list[Block]) -> str:
    """What the painting holds, in words, for a page read without scripts."""
    seen: dict[str, Block] = {}
    for animal in animals:
        seen.setdefault(str(animal.get("id", "")), animal)
    items = "".join(
        tag(
            "li",
            tag("b", b.inline(a.get("name", "")))
            + (" " + tag("i", b.inline(a["latin"])) if a.get("latin") else "")
            + ": "
            + b.inline(a.get("fact", "")),
        )
        for a in seen.values()
    )
    items += "".join(
        tag("li", tag("b", b.inline(z.get("label", ""))) + ": " + b.inline(z.get("text", "")))
        for z in zones
    )
    return tag("ul", items, class_="pa-fallback") if items else ""


def check(story: Mapping[str, Any], drawn: Mapping[str, Drawing], report: Any) -> None:
    """Animals name drawn rigs, zones and the tide fit the painting, the journal is a key."""
    art = story.get("art", {}) if isinstance(story.get("art"), Mapping) else {}
    for where, block in blocks(story, "panorama"):
        check_block(block, where, art, drawn, report)


def check_block(
    block: Block, where: str, art: Mapping[str, Any], drawn: Mapping[str, Drawing], report: Any
) -> None:
    key = str(block.get("art", ""))
    if key not in art:
        report.errors.append(f"{where}.art {key!r} is not defined in art")
    drawing = drawn.get(key)
    layers = {layer.name for layer in drawing.layers if not layer.rig} if drawing else set()
    for k, animal in enumerate(block.get("animals", [])):
        _check_animal(animal, f"{where}.animals[{k}]", art, drawn, report)
    for k, zone in enumerate(block.get("zones", [])):
        if not isinstance(zone, Mapping) or not zone.get("label"):
            report.errors.append(f"{where}.zones[{k}] needs a label, from and to")
        elif float(zone.get("to", 0)) <= float(zone.get("from", 0)):
            report.errors.append(f"{where}.zones[{k}].to must be past its from")
    tide = block.get("tide")
    if tide is not None:
        if not isinstance(tide, Mapping):
            report.errors.append(f"{where}.tide must be an object")
        else:
            for name in (tide.get("layer"), tide.get("surf")):
                if name is not None and drawing and name not in layers:
                    report.errors.append(f"{where}.tide names layer {name!r}; draw a data-layer")
            if not 0 <= float(tide.get("start", 0.5)) <= 1:
                report.errors.append(f"{where}.tide.start must be between 0 and 1")
    for name in block.get("front", []):
        if drawing and name not in layers:
            report.errors.append(f"{where}.front names layer {name!r}; draw a data-layer")
    journal = block.get("journal")
    if journal not in (None, False, True) and not keys.ID.match(str(journal)):
        report.errors.append(f"{where}.journal must be true or a key of lowercase letters and -")


def _check_animal(
    animal: Any, where: str, art: Mapping[str, Any], drawn: Mapping[str, Drawing], report: Any
) -> None:
    if not isinstance(animal, Mapping):
        report.errors.append(f"{where} must be an object")
        return
    for field in ("id", "name", "art", "at"):
        if not animal.get(field):
            report.errors.append(f"{where}.{field} is required")
    if animal.get("id") and not keys.ID.match(str(animal["id"])):
        report.errors.append(f"{where}.id must be lowercase letters, digits and -")
    key = str(animal.get("art", ""))
    if key and key not in art:
        report.errors.append(f"{where}.art {key!r} is not defined in art")
    drawing = drawn.get(key)
    if drawing is not None:
        name = animal.get("rig")
        if name is None and len(drawing.rigs) != 1:
            count = len(drawing.rigs)
            report.errors.append(f"{where}: art {key!r} has {count} rigs; name one in rig")
        elif name is not None and name not in drawing.rigs:
            report.errors.append(f"{where}.rig {name!r} is no data-rig in art {key!r}")
    if animal.get("behavior", "wander") not in BEHAVIORS:
        report.errors.append(f"{where}.behavior must be one of {', '.join(BEHAVIORS)}")
    if animal.get("tide") is not None and animal["tide"] not in TIDES:
        report.errors.append(f"{where}.tide must be low or high")
    span = animal.get("range")
    if span is not None and not (
        isinstance(span, list)
        and len(span) == 2
        and all(isinstance(v, int | float) for v in span)
        and span[0] <= span[1]
    ):
        report.errors.append(f"{where}.range must be [from, to] in painting pixels")
