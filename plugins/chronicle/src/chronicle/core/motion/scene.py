"""Motion for a painted scene: chronicle's watercolor, its moving layers, and callouts.

The story painter makes the painting from an `art` spec (an SVG drawing, a preset or
motif elements). Here it becomes images inside the SVG: the base develops from a gray
sketch into color, each moving layer plays its motion on the loop, and spots (a
numbered dot with a label at one of the drawing's anchors) come and go with the steps.
Focus darkens the painting outside the spots or layers it names.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from typing import Any

from chronicle.core.motion import stage
from chronicle.core.motion.model import Plan
from chronicle.core.motion.parts import named
from chronicle.core.motion.timeline import Point, Timeline, changes, eased, swells
from chronicle.core.story.html import tag
from chronicle.core.story.markup import plain
from chronicle.core.story.model import Report, check_text

SCENE_KEYS = {"art", "develop", "spots"}
DEVELOP = (0.6, 2.8)  # seconds the painting takes to wash from sketch into color
SHADE = 0.55
# How the story page moves each kind of layer, as (period in seconds, size): the same
# motions, played on the animation's clock.
SWAY_PERIOD = 8.2
BOB_PERIOD = 5.3
SPIN_PERIOD = 6.5
DRIFT_PERIODS = (23.9, 18.2)
FALL_SPEED = 111.0  # pixels a second
CROSS_SPEED = 45.0
# Paintings sit on paper in both themes, so their callouts keep paper colors.
INK = "#1E2026"
SPOT_SHARE = 54.0  # painting widths per spot label size


def check(
    scene: Any,
    steps: Any,
    anchors: set[str] | None,
    layers: set[str] | None,
    facts: Mapping[str, Any],
    report: Report,
) -> None:
    """Spots need ids and anchors; steps may name spots and the drawing's moving layers.

    `anchors` and `layers` are known when the art is an SVG drawing; for presets and
    motif scenes they are None and the painter checks anchors when it paints.
    """
    if not isinstance(scene, Mapping):
        return
    for key in sorted(set(scene) - SCENE_KEYS):
        report.errors.append(
            f"scene.{key} is unknown; a scene takes {', '.join(sorted(SCENE_KEYS))}"
        )
    if not isinstance(scene.get("art"), Mapping):
        report.errors.append(
            "scene.art is required: an art spec as in a story (svg, preset or elements)"
        )
    ids: set[str] = set()
    spots = scene.get("spots", [])
    for i, spot in enumerate(spots if isinstance(spots, list) else []):
        where = f"scene.spots[{i}]"
        if not isinstance(spot, Mapping) or not str(spot.get("id", "")).strip():
            report.errors.append(f"{where} needs an id")
            continue
        sid = str(spot["id"])
        if sid in ids:
            report.errors.append(f"{where}.id {sid!r} is used twice")
        ids.add(sid)
        anchor = str(spot.get("anchor", ""))
        if anchors is not None and anchor not in anchors:
            known = ", ".join(sorted(anchors)) or "none"
            report.errors.append(
                f"{where}.anchor {anchor!r} is not in the drawing (it has {known})"
            )
        check_text(str(spot.get("label", "")), f"{where}.label", "caption", facts, report)
    targets = ids | (layers or set())
    for i, step in enumerate(steps if isinstance(steps, list) else []):
        if not isinstance(step, Mapping):
            continue
        for key in ("show", "hide", "focus", "pulse"):
            value = step.get(key, [])
            for x in value if isinstance(value, list) else []:
                if x not in targets and not (layers is None and x not in ids):
                    report.errors.append(
                        f"steps[{i}].{key} names {x!r}; name a spot id or a data-layer name"
                    )


def figure(
    scene: Mapping[str, Any],
    entry: Mapping[str, Any],
    hrefs: Mapping[str, str],
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    fill_text: Callable[[str], str],
) -> tuple[str, list[str]]:
    """The painting fitted into the stage box, with its layers, labels and spots."""
    p = f"{plan.slug}-s"
    w, h = float(entry["width"]), float(entry["height"])
    anchors = {
        str(k): (float(v[0]), float(v[1])) for k, v in dict(entry.get("anchors", {})).items()
    }
    layers = list(entry.get("layers", []))
    index = {str(layer.get("name")): i for i, layer in enumerate(layers)}
    spots = [s for s in scene.get("spots", []) if isinstance(s, Mapping)]
    warnings = [
        f"spot {s.get('id')}: anchor {s.get('anchor')!r} is not in the painting"
        for s in spots
        if str(s.get("anchor")) not in anchors
    ]
    spots = [s for s in spots if str(s.get("anchor")) in anchors]
    develop = bool(scene.get("develop", True))
    defs = tag(
        "image", id=f"{p}-img", href=hrefs[str(entry["file"])], width=f"{w:.0f}", height=f"{h:.0f}"
    )
    defs += tag(
        "filter",
        tag("feColorMatrix", type="saturate", values="0")
        + tag(
            "feComponentTransfer",
            "".join(
                tag(f"feFunc{c}", type="linear", slope="1.2", intercept="-0.08") for c in "RGB"
            ),
        ),
        id=f"{p}-gray",
        color_interpolation_filters="sRGB",
    )
    paint = ""
    if develop:
        paint += tag("use", href=f"#{p}-img", filter=f"url(#{p}-gray)")
        rise = eased(DEVELOP[0], DEVELOP[1], 0.0, 1.0)
        timeline.add(f"#{p}-color, .{p}-color", "opacity", rise, rest=1.0)
    paint += tag("use", href=f"#{p}-img", id=f"{p}-color")
    for i, layer in enumerate(layers):
        x, y, lw, lh = (float(v) for v in layer["box"])
        defs += tag(
            "image",
            id=f"{p}-l{i}-img",
            href=hrefs[str(layer["file"])],
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            width=f"{lw:.1f}",
            height=f"{lh:.1f}",
        )
        copies = ""
        if develop:
            copies += tag("use", href=f"#{p}-l{i}-img", filter=f"url(#{p}-gray)")
        copies += tag("use", href=f"#{p}-l{i}-img", class_=f"{p}-color" if develop else None)
        blend = None if layer.get("blend") == "normal" else "mix-blend-mode: multiply"
        moving = tag("g", copies, id=f"{p}-l{i}", style=blend)
        _motion(
            f"#{p}-l{i}",
            str(layer.get("motion", "none")),
            float(layer.get("travel", 0)),
            i,
            plan,
            timeline,
        )
        paint += tag("g", moving, id=f"{p}-l{i}-v")
    labels = "".join(_label(lab, fill_text) for lab in entry.get("labels", []))
    shades, masks = _focus(plan, p, w, h, anchors, spots, layers, index, timeline)
    marks = "".join(
        _spot(p, k, s, anchors[str(s["anchor"])], w, fill_text) for k, s in enumerate(spots)
    )
    _steps(plan, p, spots, index, timeline)
    body = tag("defs", defs + masks)
    body += tag("rect", class_="m-print", width=f"{w:.0f}", height=f"{h:.0f}")
    body += tag("g", paint, style="isolation: isolate")
    body += tag("g", labels, class_="overlay") + shades + marks
    scale, ox, oy = stage.fit(w, h, box, most=4.0)
    return (
        tag(
            "svg",
            body,
            x=f"{ox:.1f}",
            y=f"{oy:.1f}",
            width=f"{w * scale:.1f}",
            height=f"{h * scale:.1f}",
            viewBox=f"0 0 {w:.0f} {h:.0f}",
            class_="m-scene",
        ),
        warnings,
    )


# ----------------------------------------------------------------------- layers
def _motion(
    selector: str, motion: str, travel: float, k: int, plan: Plan, timeline: Timeline
) -> None:
    """A layer's story motion as tracks on the loop; a still copy shows it at rest."""
    d = plan.duration
    phase = k * 1.7
    if motion == "sway":
        sway: list[Point] = list(_wave(d, SWAY_PERIOD, 2.2, phase))
        timeline.add(selector, "rotate", sway, rest=0.0, origin="center bottom")
    elif motion == "bob":
        timeline.add(
            selector,
            "translate",
            [(t, (0.0, v)) for t, v in _wave(d, BOB_PERIOD, travel or 4, phase)],
            rest=(0.0, 0.0),
        )
    elif motion == "drift":
        xs = _wave(d, DRIFT_PERIODS[0], travel * 1.6, 0.0, 48)
        ys = _wave(d, DRIFT_PERIODS[1], travel * 0.25, math.pi / 2, 48)
        timeline.add(
            selector,
            "translate",
            [(t, (x, y)) for (t, x), (_, y) in zip(xs, ys, strict=True)],
            rest=(0.0, 0.0),
        )
    elif motion == "spin":
        turns = max(1, round(d / SPIN_PERIOD))
        timeline.add(
            selector,
            "rotate",
            [(0.0, 0.0), (d, 360.0 * turns)],
            rest=0.0,
            origin="center",
            wraps=True,
        )
    elif motion == "fall":
        span = travel or 40
        timeline.add(
            selector,
            "translate",
            _saw(d, span / FALL_SPEED, (0.0, -span / 2), (0.0, span / 2)),
            rest=(0.0, 0.0),
            wraps=True,
        )
    elif motion == "cross":
        dist = max(1.0, travel)
        period = dist / CROSS_SPEED
        timeline.add(
            selector,
            "translate",
            _saw(d, period, (0.0, 0.0), (dist, 0.0)),
            rest=(0.0, 0.0),
            wraps=True,
        )
        fade = min(period / 3, 40 / CROSS_SPEED)
        loops = max(1, round(d / period))
        each = d / loops
        seen: list[Point] = []
        for i in range(loops):
            t = i * each
            seen += [(t, 0.0), (t + fade, 1.0), (t + each - fade, 1.0), (t + each, 0.0)]
        timeline.add(selector, "opacity", seen, rest=1.0, wraps=True)
    elif motion in ("rise", "descend"):
        sign = -1.0 if motion == "rise" else 1.0
        moved = [(t, (0.0, v)) for t, v in eased(DEVELOP[0], DEVELOP[1] + 0.2, 0.0, sign * travel)]
        timeline.add(selector, "translate", moved, rest=(0.0, sign * travel))
    elif motion == "pop":
        at = DEVELOP[1] - 0.4
        timeline.add(selector, "opacity", [(0.0, 0.0), (at, 0.0), (at + 0.5, 1.0)], rest=1.0)
        grow = [(0.0, 0.6), (at, 0.6), (at + 0.35, 1.06), (at + 0.7, 1.0)]
        timeline.add(selector, "scale", grow, rest=1.0, origin="center bottom")


def _wave(
    d: float, period: float, size: float, phase: float, samples: int = 0
) -> list[tuple[float, float]]:
    """size x sin over a whole number of periods that fills the loop."""
    loops = max(1, round(d / period))
    n = samples or loops * 16
    return [(d * i / n, size * math.sin(2 * math.pi * loops * i / n + phase)) for i in range(n + 1)]


def _saw(d: float, period: float, a: tuple[float, float], b: tuple[float, float]) -> list[Point]:
    """From a to b in each period, jumping back to a at the start of the next."""
    loops = max(1, round(d / period))
    each = d / loops
    out: list[Point] = []
    for i in range(loops):
        out += [(i * each, a), (i * each + each - 0.001, b)]
    return [*out, (d, b)]


# ------------------------------------------------------------------- callouts
def _label(lab: Mapping[str, Any], fill_text: Callable[[str], str]) -> str:
    """A label the drawing placed, set live in the theme's fonts as on the story page."""
    x, y = float(lab["x"]), float(lab["y"])
    angle = float(lab.get("angle", 0))
    return tag(
        "text",
        plain(fill_text(str(lab.get("text", "")))),
        x=f"{x:.1f}",
        y=f"{y:.1f}",
        class_=f"lbl lbl-{lab.get('style', 'hand')}",
        font_size=f"{float(lab.get('size', 28)):.1f}",
        text_anchor=str(lab.get("anchor", "start")),
        fill=str(lab.get("color") or INK),
        font_weight=str(lab.get("weight") or "") or None,
        transform=f"rotate({angle:.1f} {x:.1f} {y:.1f})" if abs(angle) > 0.05 else None,
    )


def _spot(
    p: str,
    k: int,
    spot: Mapping[str, Any],
    at: tuple[float, float],
    width: float,
    fill_text: Callable[[str], str],
) -> str:
    """A numbered dot at the anchor and its label beside it, on the side with room."""
    sid = f"{p}-sp-{spot['id']}"
    x, y = at
    # Sized to the painting, which the stage shrinks: about 16 px on a 1280 px frame.
    size = width / SPOT_SHARE
    r = size * 0.7
    dot = tag("circle", class_="m-spot-dot", cx=f"{x:.1f}", cy=f"{y:.1f}", r=f"{r:.1f}")
    dot += tag(
        "text",
        str(k + 1),
        class_="m-spot-num",
        x=f"{x:.1f}",
        y=f"{y + size * 0.3:.1f}",
        text_anchor="middle",
        font_size=f"{size * 0.8:.1f}",
    )
    label = fill_text(str(spot.get("label", "")))
    if label:
        w = len(label) * size * stage.GLYPH["sans"] + size * 1.2
        left = x + r * 1.6 if x < width * 0.62 else x - r * 1.6 - w
        dot += tag(
            "rect",
            class_="m-spot-pill",
            x=f"{left:.1f}",
            y=f"{y - size * 0.85:.1f}",
            width=f"{w:.1f}",
            height=f"{size * 1.7:.1f}",
            rx=f"{size * 0.3:.1f}",
        )
        dot += tag(
            "text",
            plain(label),
            class_="m-spot-label",
            x=f"{left + size * 0.6:.1f}",
            y=f"{y + size * 0.34:.1f}",
            font_size=f"{size:.1f}",
        )
    return tag("g", tag("g", dot, id=f"{sid}-u"), id=sid, class_="m-spot")


def _steps(
    plan: Plan, p: str, spots: list[Mapping[str, Any]], index: Mapping[str, int], timeline: Timeline
) -> None:
    """Spots and layers come and go with show and hide, and swell with pulse."""
    events: dict[str, list[tuple[float, bool]]] = {}
    for step in plan.steps:
        for k, x in enumerate(step.show):
            events.setdefault(x, []).append((step.start + 0.15 + 0.15 * min(k, 6), True))
        for x in step.hide:
            events.setdefault(x, []).append((step.start, False))
    selectors = {str(s["id"]): f"#{p}-sp-{s['id']}" for s in spots}
    selectors |= {name: f"#{p}-l{i}-v" for name, i in index.items()}
    for x, life in named(events).items():
        if x in selectors:
            timeline.add(selectors[x], "opacity", life.points(), rest=life.final)
    for s in spots:
        sid = str(s["id"])
        starts = [
            st.start + 0.3 + (0.4 if st.show else 0.0) for st in plan.steps if sid in st.pulse
        ]
        if starts:
            timeline.add(
                f"#{p}-sp-{sid}-u", "scale", swells(starts, 1.12), rest=1.0, origin="center"
            )


def _focus(
    plan: Plan,
    p: str,
    w: float,
    h: float,
    anchors: Mapping[str, tuple[float, float]],
    spots: list[Mapping[str, Any]],
    layers: list[Mapping[str, Any]],
    index: Mapping[str, int],
    timeline: Timeline,
) -> tuple[str, str]:
    """A shade over the painting with soft holes where each focus step looks."""
    at = {str(s["id"]): anchors[str(s["anchor"])] for s in spots}
    radius = 0.17 * min(w, h)
    shades = ""
    masks = ""
    for step in plan.steps:
        holes = ""
        for x in step.focus:
            if x in at:
                cx, cy = at[x]
                holes += tag("circle", cx=f"{cx:.1f}", cy=f"{cy:.1f}", r=f"{radius:.1f}")
            elif x in index:
                bx, by, bw, bh = (float(v) for v in layers[index[x]]["box"])
                holes += tag(
                    "ellipse",
                    cx=f"{bx + bw / 2:.1f}",
                    cy=f"{by + bh / 2:.1f}",
                    rx=f"{bw / 2 + 40:.1f}",
                    ry=f"{bh / 2 + 40:.1f}",
                )
        if not holes:
            continue
        mid = f"{p}-m{step.index}"
        soft = tag(
            "filter",
            tag("feGaussianBlur", stdDeviation=f"{radius * 0.25:.1f}"),
            id=f"{mid}-b",
            x="-50%",
            y="-50%",
            width="200%",
            height="200%",
        )
        masks += soft + tag(
            "mask",
            tag("rect", width=f"{w:.0f}", height=f"{h:.0f}", fill="#fff")
            + tag("g", holes, fill="#000", filter=f"url(#{mid}-b)"),
            id=mid,
            maskUnits="userSpaceOnUse",
            x="0",
            y="0",
            width=f"{w:.0f}",
            height=f"{h:.0f}",
        )
        sid = f"{p}-f{step.index}"
        shades += tag(
            "rect",
            class_="m-shade",
            id=sid,
            width=f"{w:.0f}",
            height=f"{h:.0f}",
            mask=f"url(#{mid})",
        )
        last = step.index == len(plan.steps) - 1
        moves = [(step.start, SHADE)] + ([] if last else [(step.end, 0.0)])
        timeline.add(f"#{sid}", "opacity", changes(0.0, moves, 0.6), rest=0.0)
    return shades, masks
