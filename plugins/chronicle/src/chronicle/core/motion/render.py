"""An animation.json to one self-contained SVG, whatever its kind.

The kind's module draws the figure into the stage and adds its tracks to the timeline;
this module checks the parts every kind shares, frames the figure with its title and
captions, and writes the file with the theme scoped to it.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.motion import diagram, model, scene, stage
from chronicle.core.motion.model import Plan
from chronicle.core.motion.tad import draw as tad_draw
from chronicle.core.motion.tad import spec as tad_spec
from chronicle.core.motion.tad.spec import Tad
from chronicle.core.motion.timeline import Timeline
from chronicle.core.story import theme
from chronicle.core.story.facts import fill
from chronicle.core.story.model import Report
from chronicle.core.watercolor.svg.parse import SvgError, parse


@dataclass
class Sources:
    """What the entry point read for the figure.

    `drawing` is a diagram's SVG, or a scene's SVG drawing before it is painted.
    `painting` is the painter's manifest entry for a scene, and `images` maps each of
    its files to the href the SVG embeds.
    """

    drawing: str = ""
    painting: Mapping[str, Any] | None = None
    images: Mapping[str, str] = field(default_factory=dict)


@dataclass
class Animation:
    """The finished SVG, the plan it was drawn from, and what to fix before sharing it."""

    plan: Plan
    svg: str
    warnings: list[str]


def check(
    anim: Any, facts: Mapping[str, Any], fonts: Mapping[str, Any], sources: Sources
) -> Report:
    """Problems in an animation: errors stop the build, warnings do not."""
    report = model.check(anim, facts)
    if not isinstance(anim, Mapping):
        return report
    kind = anim.get("kind")
    body = anim.get(str(kind))
    steps = anim.get("steps", [])
    if kind == "tad" and isinstance(body, Mapping):
        tad = tad_spec.read(body, report, facts)
        if tad is not None:
            tad_draw.check_steps(steps, tad, report)
    elif kind == "diagram" and isinstance(body, Mapping):
        diagram.check(sources.drawing, steps, report)
    elif kind == "scene" and isinstance(body, Mapping):
        anchors: set[str] | None = None
        layers: set[str] | None = None
        if sources.drawing:
            try:
                drawing = parse(sources.drawing)
            except SvgError as exc:
                report.errors.append(f"scene.art: {exc}")
            else:
                anchors = set(drawing.anchors)
                layers = {layer.name for layer in drawing.layers}
        scene.check(body, steps, anchors, layers, facts, report)
    try:
        report.warnings.extend(theme.scoped(anim.get("theme"), fonts, ".chr-a").warnings)
    except theme.ThemeError as exc:
        report.errors.append(str(exc))
    return report


def render(
    anim: Mapping[str, Any],
    facts: Mapping[str, Any],
    fonts: Mapping[str, Any],
    css: str,
    sources: Sources,
) -> Animation:
    """Draw a checked animation; `css` is the stylesheet of the stage and every kind."""
    kind = str(anim.get("kind"))
    tad: Tad | None = None
    floor: Callable[[Mapping[str, Any]], float] = diagram.floor
    if kind == "tad":
        found = Report()
        tad = tad_spec.read(anim["tad"], found, facts)
        if tad is None or found.errors:
            raise ValueError("; ".join(found.errors) or "the tad object is invalid")
        if not anim.get("steps"):
            anim = {**anim, "steps": tad_draw.default_steps(tad)}
        floor = _tad_floor(tad)
    plan = model.plan(anim, facts, floor)
    if tad is not None:
        tad_draw.captions(plan, tad)
    timeline = Timeline(plan.duration, plan.loop)
    frame = stage.layout(plan)
    under, over, warnings = stage.frame_parts(plan, frame, timeline)

    def words(text: str) -> str:
        return fill(text, facts)

    if tad is not None:
        figure, more = tad_draw.figure(tad, plan, frame.stage, timeline)
    elif kind == "diagram":
        figure, more = diagram.figure(sources.drawing, plan, frame.stage, timeline, words)
    elif sources.painting is None:
        raise ValueError("a scene animation needs its painting; paint it first")
    else:
        figure, more = scene.figure(
            anim["scene"], sources.painting, sources.images, plan, frame.stage, timeline, words
        )
    look = theme.scoped(anim.get("theme"), fonts, f".chr-a-{plan.slug}", frozenset({"mono"}))
    svg = stage.document(plan, look.css, look.fonts_url, [css], under, figure, over, timeline)
    return Animation(plan, svg, warnings + more + look.warnings)


def _tad_floor(tad: Tad) -> Callable[[Mapping[str, Any]], float]:
    return lambda raw: tad_draw.floor(raw, tad)
