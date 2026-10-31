"""An animation.json to one self-contained SVG, whatever its kind.

The kind draws the figure into the stage and adds its tracks to the timeline; this
module checks the parts every kind shares, frames the figure with its title and
captions, and writes the file with the theme scoped to it. Kinds come from the
registry: the engine brings `diagram`, and plugins add their own.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chronicle_engine import registry
from chronicle_engine.core.motion import (  # noqa: F401  (diagram registers its kind)
    diagram,
    model,
    stage,
)
from chronicle_engine.core.motion.model import Plan
from chronicle_engine.core.motion.timeline import Timeline
from chronicle_engine.core.story import theme
from chronicle_engine.core.story.facts import fill
from chronicle_engine.core.story.model import Report
from chronicle_engine.registry import Sources

__all__ = ["Animation", "Sources", "check", "render"]


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
    kind = registry.KINDS.get(str(anim.get("kind")))
    if kind is not None and isinstance(anim.get(str(anim.get("kind"))), Mapping):
        kind.check(anim, facts, sources, report)
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
    kind = registry.KINDS[str(anim.get("kind"))]
    prepared = kind.prepare(anim, facts)
    plan = model.plan(prepared.anim, facts, prepared.floor)
    if prepared.after_plan is not None:
        prepared.after_plan(plan)
    timeline = Timeline(plan.duration, plan.loop)
    frame = stage.layout(plan)
    under, over, warnings = stage.frame_parts(plan, frame, timeline)

    def words(text: str) -> str:
        return fill(text, facts)

    figure, more = kind.figure(prepared.anim, prepared, plan, frame.stage, timeline, sources, words)
    look = theme.scoped(anim.get("theme"), fonts, f".chr-a-{plan.slug}", frozenset({"mono"}))
    svg = stage.document(plan, look.css, look.fonts_url, [css], under, figure, over, timeline)
    return Animation(plan, svg, warnings + more + look.warnings)
