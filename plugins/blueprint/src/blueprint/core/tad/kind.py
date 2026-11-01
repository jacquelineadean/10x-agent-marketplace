"""The `tad` animation kind: a technical architecture diagram written as data.

Code places the components, routes the links and runs the flows; see `spec.py`, `layout.py`,
`route.py` and `draw.py`.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from chronicle_engine.core.motion import stage
from chronicle_engine.core.motion.model import Plan
from chronicle_engine.core.motion.timeline import Timeline
from chronicle_engine.core.story.model import Report
from chronicle_engine.registry import Kind, Prepared, Sources

from blueprint.core.tad import draw, spec
from blueprint.core.tad.spec import Tad


def _check(
    anim: Mapping[str, Any], facts: Mapping[str, Any], sources: Sources, report: Report
) -> None:
    tad = spec.read(anim["tad"], report, facts)
    if tad is not None:
        draw.check_steps(anim.get("steps", []), tad, report)


def _prepare(anim: Mapping[str, Any], facts: Mapping[str, Any]) -> Prepared:
    found = Report()
    tad = spec.read(anim["tad"], found, facts)
    if tad is None or found.errors:
        raise ValueError("; ".join(found.errors) or "the tad object is invalid")
    if not anim.get("steps"):
        anim = {**anim, "steps": draw.default_steps(tad)}
    return Prepared(anim, _floor(tad), lambda plan: draw.captions(plan, tad), tad)


def _floor(tad: Tad) -> Callable[[Mapping[str, Any]], float]:
    return lambda raw: draw.floor(raw, tad)


def _figure(
    anim: Mapping[str, Any],
    prepared: Prepared,
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    sources: Sources,
    words: Callable[[str], str],
) -> tuple[str, list[str]]:
    tad: Tad = prepared.state
    return draw.figure(tad, plan, box, timeline)


TAD = Kind(
    skeleton={
        "direction": "right",
        "groups": [],
        "nodes": [{"id": "client", "label": "Client", "kind": "client"}],
        "edges": [],
        "flows": [],
    },
    next_step="write the nodes, groups, edges and flows",
    check=_check,
    prepare=_prepare,
    figure=_figure,
)
