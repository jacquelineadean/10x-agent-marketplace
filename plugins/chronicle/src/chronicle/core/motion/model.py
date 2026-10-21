"""The animation format: what an animation.json may hold, its checks, and its clock.

An animation is one figure that moves on its own and plays anywhere: a painted scene, a
drawn diagram or a technical architecture diagram (TAD). It plays as a list of steps.
Each step has a caption and names what happens to which parts of the figure:

    show, hide   parts appear or leave (an edge draws itself from its source)
    focus        every other part dims for this step
    draw         lines draw themselves on
    flow         a packet travels along paths or a TAD flow, in order
    pulse        parts swell once to catch the eye
    state        TAD parts turn new, legacy, good, warn, bad, down, planned or normal

Durations come from code: reading time for the caption, plus the time packets need.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.story.facts import fill
from chronicle.core.story.model import Report, check_text

SCHEMA_VERSION = 1
KINDS = ("scene", "diagram", "tad")
SIZES = {
    "16:9": (1280, 720),
    "4:3": (1024, 768),
    "1:1": (1080, 1080),
    "4:5": (1080, 1350),
    "9:16": (1080, 1920),
    "wide": (1600, 700),
}
ACTIONS = ("show", "hide", "focus", "draw", "flow", "pulse", "state")
KIND_ACTIONS = {
    "scene": ("show", "hide", "focus", "pulse"),
    "diagram": ("show", "hide", "focus", "draw", "flow", "pulse"),
    "tad": ACTIONS,
}
THEME_KEYS = ("concept", "palette", "dark", "fonts")
BACKGROUNDS = ("paper", "surface", "none")
THEME_MODES = ("auto", "light", "dark")
TOP_KEYS = {"schema_version", "kind", "meta", "theme", "frame", "timing", "steps", "facts_file"}
# Reading pace for captions: about 190 words a minute after a short settle.
SETTLE = 1.0
WORDS_PER_SECOND = 3.2
MIN_STEP = 2.2
MAX_STEP = 12.0
_SLUG = re.compile(r"[^a-z0-9]+")


@dataclass
class Step:
    """One beat of the animation, placed on the clock."""

    index: int
    caption: str
    start: float
    duration: float
    show: list[str] = field(default_factory=list)
    hide: list[str] = field(default_factory=list)
    focus: list[str] = field(default_factory=list)
    draw: list[str] = field(default_factory=list)
    flow: list[str] = field(default_factory=list)
    pulse: list[str] = field(default_factory=list)
    state: dict[str, str] = field(default_factory=dict)

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class Plan:
    """Everything the stage needs: frame, words, clock and steps with their times."""

    kind: str
    slug: str
    width: int
    height: int
    title: str
    kicker: str
    description: str
    credit: str
    sources: list[dict[str, str]]
    show_title: bool
    captions: bool
    progress: bool
    background: str
    theme_mode: str
    loop: bool
    lead: float
    hold: float
    steps: list[Step]
    duration: float

    @property
    def unit(self) -> float:
        """Type scale: 1 at 1280 x 720, larger for bigger and taller frames."""
        return max(0.6, float((self.width * self.height) ** 0.5) / 960)

    def step_at(self, t: float) -> Step | None:
        for step in self.steps:
            if step.start <= t < step.end:
                return step
        return None


def check(anim: Any, facts: Mapping[str, Any]) -> Report:
    """Validate the parts every kind shares; the kind's own module checks the rest."""
    report = Report()
    if not isinstance(anim, Mapping):
        report.errors.append("an animation must be a JSON object")
        return report
    if anim.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        report.errors.append(f"schema_version must be {SCHEMA_VERSION}")
    for key in sorted(set(anim) - TOP_KEYS - set(KINDS)):
        report.warnings.append(f"{key} is not used; an animation takes {', '.join(TOP_KEYS)}")
    kind = anim.get("kind")
    if kind not in KINDS:
        report.errors.append(f"kind must be one of {', '.join(KINDS)}")
    elif not isinstance(anim.get(kind), Mapping):
        report.errors.append(f"a {kind} animation needs a {kind!r} object")
    meta = anim.get("meta")
    if not isinstance(meta, Mapping) or not str(meta.get("title", "")).strip():
        report.errors.append("meta.title is required")
    elif not str(meta.get("description", "")).strip():
        report.errors.append(
            "meta.description is required: one sentence that says what the animation shows, "
            "used as its alt text and as the caption of a still copy"
        )
    theme = anim.get("theme", {})
    if isinstance(theme, Mapping):
        for key in sorted(set(theme) - set(THEME_KEYS)):
            report.warnings.append(f"theme.{key} is for story pages; animations use {THEME_KEYS}")
    _check_frame(anim.get("frame", {}), report)
    steps = anim.get("steps", [])
    if not isinstance(steps, list):
        report.errors.append("steps must be a list")
        steps = []
    allowed = KIND_ACTIONS.get(str(kind), ACTIONS)
    for i, step in enumerate(steps):
        where = f"steps[{i}]"
        if not isinstance(step, Mapping):
            report.errors.append(f"{where} must be an object")
            continue
        for key in sorted(set(step) - {"caption", "duration", *ACTIONS}):
            report.errors.append(f"{where}.{key} is unknown; a step takes caption, duration, ...")
        for key in ACTIONS:
            if key in step and key not in allowed:
                report.errors.append(f"{where}.{key} does not apply to a {kind} animation")
        for key in ("show", "hide", "focus", "draw", "flow", "pulse"):
            value = step.get(key, [])
            if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
                report.errors.append(f"{where}.{key} must be a list of ids")
        if "state" in step and not isinstance(step["state"], Mapping):
            report.errors.append(f"{where}.state must map ids to states")
        duration = step.get("duration")
        if duration is not None and not (
            isinstance(duration, int | float) and 0.5 <= duration <= 60
        ):
            report.errors.append(f"{where}.duration must be seconds between 0.5 and 60")
        caption = step.get("caption", "")
        if not isinstance(caption, str):
            report.errors.append(f"{where}.caption must be text")
        else:
            check_text(caption, f"{where}.caption", "caption", facts, report)
    for key in ("title", "kicker", "description", "credit"):
        text = meta.get(key, "") if isinstance(meta, Mapping) else ""
        if isinstance(text, str):
            check_text(text, f"meta.{key}", "caption", facts, report)
    return report


def _check_frame(frame: Any, report: Report) -> None:
    if not isinstance(frame, Mapping):
        report.errors.append("frame must be an object")
        return
    size = frame.get("size", "16:9")
    if size not in SIZES and "width" not in frame:
        report.errors.append(f"frame.size must be one of {', '.join(SIZES)}, or give width")
    for key in ("width", "height"):
        value = frame.get(key)
        if value is not None and not (isinstance(value, int) and 320 <= value <= 3840):
            report.errors.append(f"frame.{key} must be whole pixels between 320 and 3840")
    if frame.get("background", "paper") not in BACKGROUNDS:
        report.errors.append(f"frame.background must be one of {', '.join(BACKGROUNDS)}")
    if frame.get("theme", "auto") not in THEME_MODES:
        report.errors.append(f"frame.theme must be one of {', '.join(THEME_MODES)}")


def plan(
    anim: Mapping[str, Any],
    facts: Mapping[str, Any],
    floor: Callable[[Mapping[str, Any]], float] | None = None,
) -> Plan:
    """Place the steps on the clock. `floor` gives the least time a step's actions need."""
    meta = dict(anim.get("meta", {}))
    frame = dict(anim.get("frame", {}))
    timing = dict(anim.get("timing", {}))
    width, height = SIZES.get(str(frame.get("size", "16:9")), SIZES["16:9"])
    width = int(frame.get("width", width))
    height = int(frame.get("height", height if "width" not in frame else round(width * 9 / 16)))
    pace = float(timing.get("pace", 1.0))
    lead = float(timing.get("lead", 0.6))
    hold = float(timing.get("hold", 2.0))
    steps: list[Step] = []
    clock = lead
    for i, raw in enumerate(anim.get("steps", [])):
        caption = fill(str(raw.get("caption", "")), facts)
        need = floor(raw) if floor else 0.0
        if raw.get("duration") is not None:
            duration = float(raw["duration"])
        else:
            duration = min(MAX_STEP, max(MIN_STEP, reading_time(caption), need) * pace)
        steps.append(
            Step(
                index=i,
                caption=caption,
                start=clock,
                duration=duration,
                show=list(raw.get("show", [])),
                hide=list(raw.get("hide", [])),
                focus=list(raw.get("focus", [])),
                draw=list(raw.get("draw", [])),
                flow=list(raw.get("flow", [])),
                pulse=list(raw.get("pulse", [])),
                state={str(k): str(v) for k, v in dict(raw.get("state", {})).items()},
            )
        )
        clock += duration
    duration = clock + hold
    if not steps:
        duration = max(duration, float(timing.get("duration", 8.0)))
    title = fill(str(meta.get("title", "")), facts)
    return Plan(
        kind=str(anim.get("kind")),
        slug=slug(title),
        width=width,
        height=height,
        title=title,
        kicker=fill(str(meta.get("kicker", "")), facts),
        description=fill(str(meta.get("description", "")), facts),
        credit=fill(str(meta.get("credit", "")), facts),
        sources=[
            {k: str(v) for k, v in s.items() if k in ("label", "detail", "url")}
            for s in meta.get("sources", [])
            if isinstance(s, Mapping)
        ],
        show_title=bool(frame.get("title", True)),
        captions=bool(frame.get("captions", True)) and bool(steps),
        progress=bool(frame.get("progress", True)) and len(steps) > 1,
        background=str(frame.get("background", "paper")),
        theme_mode=str(frame.get("theme", "auto")),
        loop=bool(timing.get("loop", True)),
        lead=lead,
        hold=hold,
        steps=steps,
        duration=duration,
    )


def reading_time(text: str) -> float:
    """Seconds to read a caption once, with a moment to look at the figure first."""
    words = len(text.split())
    return SETTLE + words / WORDS_PER_SECOND if words else 0.0


def slug(title: str) -> str:
    """A CSS-safe name for one animation, so several can share a page."""
    base = _SLUG.sub("-", title.lower()).strip("-")[:24].strip("-")
    return f"a-{base or 'figure'}"


def ids_in(step: Step) -> list[tuple[str, str]]:
    """Every (action, id) a step names, for checks that all ids exist."""
    out: list[tuple[str, str]] = []
    for key in ("show", "hide", "focus", "draw", "flow", "pulse"):
        out.extend((key, i) for i in getattr(step, key))
    out.extend(("state", i) for i in step.state)
    return out
