"""Motion for a drawn diagram: Claude's own SVG, rebuilt from the allowlist, played by id.

The drawing is the story diagram format (classes such as `box`, `line`, `f-accent`). Steps
name its element ids. A part named first in `show` or `draw` starts hidden; `draw` also
strokes its lines on; `flow` runs a packet along paths in order; `focus` dims every other
part that has an id. Parts that dim or pulse are wrapped in groups, so those effects and
showing never fight over one property.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from chronicle.core.motion import stage
from chronicle.core.motion.model import Plan, Step
from chronicle.core.motion.parts import Life, named, packet
from chronicle.core.motion.timeline import Timeline, changes, redraws, swells
from chronicle.core.story.diagram import DiagramError, sanitize
from chronicle.core.story.model import Report

DRAWN = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}
ROUTES = {"path", "line", "polyline"}
# Elements that are part of another element or never drawn, so steps cannot name them.
INNER = {"tspan", "stop", "title", "desc", "defs", "marker", "linearGradient", "symbol"}
DIM = 0.2
STAGGER = 0.12
DRAW_TIME = 0.9
HOP_MIN, HOP_MAX = 0.5, 1.4
TRAIL = 0.07  # share of a path the packet's trail covers


@dataclass
class _Part:
    el: ET.Element
    parent: ET.Element | None
    inner: bool  # inside a part that steps cannot name, such as a marker or text


def check(source: str, steps: Any, report: Report) -> None:
    """The drawing passes the sanitizer and every id a step names is a part of it."""
    try:
        parts = _parts(ET.fromstring(sanitize(source, "check").markup), "check")  # noqa: S314 - markup is the sanitizer's own output
    except DiagramError as exc:
        report.errors.append(f"diagram: {exc}")
        return
    for i, step in enumerate(steps if isinstance(steps, list) else []):
        if not isinstance(step, Mapping):
            continue
        for key in ("show", "hide", "focus", "draw", "pulse", "flow"):
            value = step.get(key, [])
            for x in value if isinstance(value, list) else []:
                part = parts.get(str(x))
                where = f"steps[{i}].{key}"
                if part is None:
                    report.errors.append(f"{where} names {x!r}; the drawing has no such id")
                elif part.inner:
                    report.errors.append(
                        f"{where} names {x!r}, which sits inside text, defs or a marker; "
                        "name the element around it"
                    )
                elif key == "flow" and _name(part.el) not in ROUTES:
                    report.errors.append(
                        f"{where} names {x!r}, a <{_name(part.el)}>; flow runs along a path, "
                        "line or polyline, drawn in the direction of travel"
                    )


def floor(raw: Mapping[str, Any]) -> float:
    """Time a step needs for its lines to draw and its packets to travel."""
    need = DRAW_TIME + 0.6 if raw.get("draw") else 0.0
    hops = len(raw.get("flow", []))
    return max(need, 0.4 + hops * 0.8 + 0.6) if hops else need


def figure(
    source: str,
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    fill_text: Callable[[str], str],
) -> tuple[str, list[str]]:
    """The drawing fitted into the stage box; its tracks go on the timeline."""
    prefix = f"{plan.slug}-d"
    drawing = sanitize(source, prefix, fill_text)
    root = ET.fromstring(drawing.markup)  # noqa: S314 - markup is the sanitizer's own output
    found = _parts(root, prefix)
    lives = _lives(plan, found)
    focus = _dimmed(plan, found, root)
    pulses = {x for s in plan.steps for x in s.pulse}
    warnings: list[str] = []
    for x, part in found.items():
        if x in focus or x in pulses:
            _wrap(part, f"{prefix}-{x}")
        life = lives.get(x)
        if life is not None and life.moves:
            timeline.add(f"#{prefix}-{x}", "opacity", life.points(), rest=life.final)
    for x, values in focus.items():
        timeline.add(f"#{prefix}-{x}-d", "opacity", changes(1.0, values), rest=1.0)
    for x in pulses:
        starts = [
            s.start + 0.3 + (0.5 if s.show or s.draw else 0.0) for s in plan.steps if x in s.pulse
        ]
        timeline.add(f"#{prefix}-{x}-u", "scale", swells(starts), rest=1.0, origin="center")
    _draws(plan, found, prefix, timeline, warnings)
    _flows(plan, found, prefix, timeline)
    scale, ox, oy = stage.fit(drawing.width, drawing.height, box, most=1.6 * plan.unit)
    root.set("x", f"{ox:.1f}")
    root.set("y", f"{oy:.1f}")
    root.set("width", f"{drawing.width * scale:.1f}")
    root.set("height", f"{drawing.height * scale:.1f}")
    return ET.tostring(root, encoding="unicode"), warnings


# ------------------------------------------------------------------------ parts
def _name(el: ET.Element) -> str:
    return el.tag.rsplit("}", 1)[-1]


def _parts(root: ET.Element, prefix: str) -> dict[str, _Part]:
    """Every element with an id, by the id Claude gave it, with its parent."""
    out: dict[str, _Part] = {}

    def walk(el: ET.Element, parent: ET.Element | None, inner: bool) -> None:
        raw = el.get("id", "")
        if raw.startswith(prefix + "-"):
            out[raw[len(prefix) + 1 :]] = _Part(el, parent, inner or _name(el) in INNER)
        for child in el:
            walk(child, el, inner or _name(el) in INNER | {"text"})

    walk(root, None, False)
    return out


def _wrap(part: _Part, base: str) -> None:
    """Put the element inside a dim group and a pulse group, in the same place."""
    if part.parent is None:
        return
    index = list(part.parent).index(part.el)
    part.parent.remove(part.el)
    outer = ET.Element("g", {"id": f"{base}-d"})
    inner = ET.SubElement(outer, "g", {"id": f"{base}-u"})
    inner.append(part.el)
    part.parent.insert(index, outer)
    part.parent = inner


def _lives(plan: Plan, found: Mapping[str, _Part]) -> dict[str, Life]:
    events: dict[str, list[tuple[float, bool]]] = {}
    for step in plan.steps:
        shown = list(dict.fromkeys([*step.show, *step.draw]))
        for k, x in enumerate(shown):
            events.setdefault(x, []).append((step.start + 0.1 + min(k, 8) * STAGGER, True))
        for x in step.hide:
            events.setdefault(x, []).append((step.start, False))
    return named({x: ev for x, ev in events.items() if x in found})


def _dimmed(
    plan: Plan, parts: Mapping[str, _Part], root: ET.Element
) -> dict[str, list[tuple[float, float]]]:
    """For each outermost part outside a step's focus, its opacity at each step."""
    if not any(s.focus for s in plan.steps):
        return {}
    above: dict[str, set[str]] = {x: set() for x in parts}
    lookup = {id(p.el): x for x, p in parts.items()}

    def walk(el: ET.Element, chain: list[str]) -> None:
        mine = lookup.get(id(el))
        if mine is not None:
            above[mine] = set(chain)
            chain = [*chain, mine]
        for child in el:
            walk(child, chain)

    walk(root, [])
    free = [x for x, p in parts.items() if not p.inner]
    out: dict[str, list[tuple[float, float]]] = {}
    for step in plan.steps:
        keep = set(step.focus)
        keep |= {a for x in step.focus for a in above.get(x, set())}
        keep |= {x for x in free if above[x] & set(step.focus)}
        for x in free:
            lit = not step.focus or x in keep
            outermost = not (above[x] - keep)
            value = 1.0 if lit or not outermost else DIM
            out.setdefault(x, []).append((step.start, value))
    return {x: v for x, v in out.items() if any(p[1] < 1 for p in v)}


# ------------------------------------------------------------------------ lines
def _draws(
    plan: Plan, parts: Mapping[str, _Part], prefix: str, timeline: Timeline, warnings: list[str]
) -> None:
    """Strokes under each part named in `draw` grow on from their start."""
    starts: dict[str, list[float]] = {}
    for step in plan.steps:
        for k, x in enumerate(step.draw):
            starts.setdefault(x, []).append(step.start + 0.1 + min(k, 8) * STAGGER)
    count = 0
    for x, times in starts.items():
        for el in parts[x].el.iter():
            if (
                _name(el) not in DRAWN
                or el.get("stroke-dasharray")
                or "dashed" in el.get("class", "").split()
            ):
                continue
            count += 1
            eid = el.get("id") or f"{prefix}-w{count}"
            el.set("id", eid)
            el.set("pathLength", "1")
            el.set("stroke-dasharray", "1 1")
            points = redraws(1.0, times, DRAW_TIME, False)
            timeline.add(f"#{eid}", "stroke-dashoffset", points, rest=0.0)
    if starts and not count:
        warnings.append("draw names parts with no solid stroke to draw; they fade in instead")


def _flows(plan: Plan, found: Mapping[str, _Part], prefix: str, timeline: Timeline) -> None:
    """A packet runs along each path a step's flow names, one path after another."""
    count = 0
    for step in plan.steps:
        if not step.flow:
            continue
        start = step.start + _lag(step)
        each = min(HOP_MAX, max(HOP_MIN, (step.end - 0.45 - start) / len(step.flow)))
        for k, x in enumerate(step.flow):
            part = found[x]
            d = _path_data(part.el)
            if not d or part.parent is None:
                continue
            count += 1
            t0 = start + k * each
            markup = packet(
                f"{prefix}-pk{count}",
                d,
                1.0,
                TRAIL,
                (t0, t0 + each * 0.92),
                True,
                timeline,
                unit_length=True,
                transform=part.el.get("transform"),
            )
            parent = part.parent
            runner = ET.fromstring(markup)  # noqa: S314 - markup built here from escaped values
            parent.insert(list(parent).index(part.el) + 1, runner)


def _lag(step: Step) -> float:
    return 0.4 + (0.6 if step.show or step.draw else 0.0)


def _path_data(el: ET.Element) -> str:
    name = _name(el)
    if name == "path":
        return str(el.get("d", ""))
    if name == "line":
        return f"M{el.get('x1', '0')} {el.get('y1', '0')} L{el.get('x2', '0')} {el.get('y2', '0')}"
    numbers = str(el.get("points", "")).replace(",", " ").split()
    pairs = [f"{numbers[i]} {numbers[i + 1]}" for i in range(0, len(numbers) - 1, 2)]
    return "M" + " L".join(pairs) if len(pairs) > 1 else ""
