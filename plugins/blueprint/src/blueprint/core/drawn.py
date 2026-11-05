"""Kinds that generate a drawing in the diagram format and then play as a `diagram`.

The sequence and ERD kinds write SVG markup from data, with an id on every part, and hand
it to the engine's diagram kind for checks, timing and motion. The drawing passes the same
sanitizer as one Claude draws.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from chronicle_engine.core.motion import diagram, stage
from chronicle_engine.core.motion.model import Plan
from chronicle_engine.core.motion.timeline import Timeline
from chronicle_engine.core.story.html import escape
from chronicle_engine.core.story.model import Report
from chronicle_engine.registry import Kind, Prepared, Sources

Spec = Mapping[str, Any]


def kind(
    name: str,
    draw: Callable[[Spec], str],
    validate: Callable[[Spec, Report], None],
    default_steps: Callable[[Spec], list[dict[str, Any]]],
    skeleton: Mapping[str, Any],
    next_step: str,
) -> Kind:
    """A Kind whose drawing code writes from the animation's `name` object."""

    def check(
        anim: Mapping[str, Any], facts: Mapping[str, Any], sources: Sources, report: Report
    ) -> None:
        validate(anim.get(name, {}), report)
        if report.ok:
            diagram.check(sources.drawing, anim.get("steps") or default_steps(anim[name]), report)

    def prepare(anim: Mapping[str, Any], facts: Mapping[str, Any]) -> Prepared:
        if not anim.get("steps"):
            anim = {**anim, "steps": default_steps(anim[name])}
        return Prepared(anim, diagram.floor)

    def figure(
        prepared: Prepared,
        plan: Plan,
        box: stage.Box,
        timeline: Timeline,
        sources: Sources,
        words: Callable[[str], str],
    ) -> tuple[str, list[str]]:
        return diagram.figure(sources.drawing, plan, box, timeline, words)

    def drawing(body: Mapping[str, Any]) -> str:
        report = Report()
        validate(body, report)
        if report.errors:
            raise ValueError("; ".join(report.errors))
        return draw(body)

    return Kind(
        skeleton=skeleton,
        next_step=next_step,
        check=check,
        prepare=prepare,
        figure=figure,
        drawing=drawing,
    )


def text(cls: str, x: float, y: float, words: Any, anchor: str = "start") -> str:
    """One text element; `anchor` is start, middle or end."""
    where = f'x="{x:g}" y="{y:g}"' + (f' text-anchor="{anchor}"' if anchor != "start" else "")
    return f'<text class="{cls}" {where}>{escape(words)}</text>'


def svg(width: float, height: float, body: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}">{body}</svg>'
    )


def head(x: float, y: float, direction: float, filled: bool) -> str:
    """An arrowhead pointing along x (direction 1 right, -1 left) with its tip at x, y."""
    back = x - 9 * direction
    points = f"M{back:g} {y - 4.5:g} L{x:g} {y:g} L{back:g} {y + 4.5:g}"
    if filled:
        return f'<path class="head" d="{points} Z"/>'
    return f'<path class="line" d="{points}"/>'
