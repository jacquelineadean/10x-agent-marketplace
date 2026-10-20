"""The frame around a moving figure: title, captions, the step strip, and the SVG file.

The figure itself (a scene, a diagram, a TAD) is drawn by its kind's module into the
stage box this module hands it. Everything is one self-contained SVG: the theme's
tokens scoped to the figure, its own stylesheet and keyframes, and no script, so it
plays as an image in a README, a wiki or a slide and stays still and whole where
animation is off.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from chronicle.core.motion.model import Plan
from chronicle.core.motion.timeline import TAU, Point, Timeline, changes
from chronicle.core.story.html import tag
from chronicle.core.story.markup import plain

# Average glyph width as a share of the font size, by font kind, for wrapping text the
# browser will set; slightly wide so lines fit.
GLYPH = {"serif": 0.5, "sans": 0.55, "mono": 0.61, "hand": 0.46, "display": 0.48}


@dataclass(frozen=True)
class Box:
    """A rectangle in frame pixels."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Layout:
    """Where the frame's parts go, all in frame pixels."""

    stage: Box
    caption: Box | None
    strip: Box | None
    pad: float
    unit: float


def layout(plan: Plan) -> Layout:
    """Split the frame into header, stage, caption band and step strip."""
    u = plan.unit
    pad = 36 * u
    top = pad + (60 * u if plan.show_title else 0)
    bottom = plan.height - pad
    strip = None
    if plan.progress:
        strip = Box(pad, bottom - 3 * u, plan.width - 2 * pad, 3 * u)
        bottom -= 19 * u
    caption = None
    if plan.captions:
        line = caption_size(plan) * 1.3
        caption = Box(pad, bottom - 2 * line, plan.width - 2 * pad, 2 * line)
        bottom = caption.y - 18 * u
    stage = Box(pad, top + 10 * u, plan.width - 2 * pad, max(40.0, bottom - top - 10 * u))
    return Layout(stage, caption, strip, pad, u)


def caption_size(plan: Plan) -> float:
    return 21 * plan.unit


def fit(width: float, height: float, box: Box, most: float = 1.4) -> tuple[float, float, float]:
    """Scale and offset that center a width x height figure in the box."""
    scale = min(box.w / max(width, 1), box.h / max(height, 1), most)
    return scale, box.x + (box.w - width * scale) / 2, box.y + (box.h - height * scale) / 2


def wrap(text: str, width: float, size: float, kind: str = "serif") -> list[str]:
    """Greedy line breaks for text set at `size` px in a box `width` px wide."""
    most = max(8, int(width / (size * GLYPH.get(kind, 0.55))))
    lines: list[str] = []
    line = ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if len(trial) > most and line:
            lines.append(line)
            line = word
        else:
            line = trial
    if line:
        lines.append(line)
    return lines


def text(
    lines: Sequence[str], x: float, y: float, size: float, css: str, **attrs: str | None
) -> str:
    """A <text> with one tspan per line, 1.3 lines apart."""
    spans = "".join(
        tag("tspan", plain(line), x=f"{x:.1f}", dy="0" if i == 0 else f"{size * 1.3:.1f}")
        for i, line in enumerate(lines)
    )
    return tag(
        "text", spans, x=f"{x:.1f}", y=f"{y:.1f}", class_=css, font_size=f"{size:.1f}", **attrs
    )


def frame_parts(plan: Plan, box: Layout, timeline: Timeline) -> tuple[str, str, list[str]]:
    """The header, captions and strip as markup under and over the figure, plus warnings."""
    u = plan.unit
    warnings: list[str] = []
    under = ""
    if plan.background != "none":
        css = "a-bg surface" if plan.background == "surface" else "a-bg"
        under += tag("rect", class_=css, width=plan.width, height=plan.height)
    if plan.show_title:
        kick = box.pad + 13 * u
        if plan.kicker:
            under += text([plan.kicker.upper()], box.pad, kick, 12.5 * u, "a-kicker")
        title_y = kick + (40 * u if plan.kicker else 26 * u)
        under += text([plan.title], box.pad, title_y, 31 * u, "a-title")
        if len(plan.title) * 31 * u * GLYPH["display"] > box.stage.w * 0.92:
            warnings.append("meta.title is too long for one line in this frame; shorten it")
    if plan.credit:
        under += text(
            [plan.credit],
            plan.width - box.pad,
            box.pad + 13 * u,
            12 * u,
            "a-credit",
            text_anchor="end",
        )
    over = ""
    if box.caption is not None:
        over += _captions(plan, box.caption, timeline, warnings)
    if box.strip is not None:
        over += _strip(plan, box.strip, timeline)
    return under, over, warnings


def _captions(plan: Plan, band: Box, timeline: Timeline, warnings: list[str]) -> str:
    u = plan.unit
    size = caption_size(plan)
    indent = 46 * u
    out = ""
    for step in plan.steps:
        if not step.caption:
            continue
        lines = wrap(step.caption, band.w - indent, size)
        fitted = size
        if len(lines) > 2:
            fitted = size * 0.86
            lines = wrap(step.caption, band.w - indent, fitted)
        if len(lines) > 2:
            warnings.append(
                f"steps[{step.index}].caption runs to {len(lines)} lines; keep captions under "
                f"about {int(2 * (band.w - indent) / (size * GLYPH['serif']) / 6)} words"
            )
        cid = f"{plan.slug}-cap-{step.index}"
        num = text([f"{step.index + 1:02d}"], band.x, band.y + size * 0.95, 13.5 * u, "a-num")
        body = text(lines, band.x + indent, band.y + fitted * 0.95, fitted, "a-cap")
        out += tag("g", num + body, id=cid)
        last = step.index == len(plan.steps) - 1
        timeline.add(f"#{cid}", "opacity", _during(step.start, step.end, last), rest=0.0)
    if plan.description:
        rid = f"{plan.slug}-cap-rest"
        lines = wrap(plan.description, band.w, size * 0.9)[:2]
        out += tag("g", text(lines, band.x, band.y + size * 0.9, size * 0.9, "a-cap"), id=rid)
        timeline.add(f"#{rid}", "opacity", [(0.0, 0.0)], rest=1.0)
    return out


def _during(start: float, end: float, last: bool) -> list[Point]:
    """Visible from `start` to `end`; the last caption stays up through the hold."""
    if last:
        return changes(0.0, [(start, 1.0)])
    return changes(0.0, [(start, 1.0), (max(start + TAU, end - TAU / 2), 0.0)])


def _strip(plan: Plan, strip: Box, timeline: Timeline) -> str:
    """One segment per step that fills while its step plays."""
    gap = 6 * plan.unit
    n = len(plan.steps)
    width = (strip.w - gap * (n - 1)) / n
    y = strip.y + strip.h / 2
    out = ""
    for step in plan.steps:
        x = strip.x + step.index * (width + gap)
        line = {"x1": f"{x:.1f}", "y1": f"{y:.1f}", "x2": f"{x + width:.1f}", "y2": f"{y:.1f}"}
        out += tag("line", class_="a-track", stroke_width=f"{strip.h:.1f}", **line)
        fid = f"{plan.slug}-fill-{step.index}"
        out += tag(
            "line",
            id=fid,
            class_="a-fill",
            stroke_width=f"{strip.h:.1f}",
            stroke_dasharray=f"{width:.1f} {width + 1:.1f}",
            **line,
        )
        timeline.add(
            f"#{fid}",
            "stroke-dashoffset",
            [(0.0, width), (step.start, width), (step.end, 0.0)],
            rest=0.0,
        )
    gid = f"{plan.slug}-strip"
    timeline.add(f"#{gid}", "opacity", [(0.0, 1.0)], rest=0.0)
    return tag("g", out, id=gid)


def document(
    plan: Plan,
    look_css: str,
    fonts_url: str,
    styles: Sequence[str],
    under: str,
    figure: str,
    over: str,
    timeline: Timeline,
) -> str:
    """The finished SVG: one file with its fonts, styles, keyframes and alt text."""
    scope = f".chr-a-{plan.slug}"
    reduce = (
        "@media (prefers-reduced-motion: reduce) {\n"
        f"  {scope}, {scope} * {{ animation: none !important; }}\n}}\n"
    )
    imports = f'@import url("{fonts_url}");\n' if fonts_url else ""
    css = imports + look_css + "".join(styles) + timeline.css(plan.slug) + reduce
    steps = " ".join(f"{s.index + 1}. {s.caption}" for s in plan.steps if s.caption)
    sources = "; ".join(
        x["label"] + (f" ({x['detail']})" if x.get("detail") else "") for x in plan.sources
    )
    desc = plan.description + (f" Steps: {steps}" if steps else "")
    desc += f" Sources: {sources}." if sources else ""
    body = (
        tag("title", plain(plan.title), id=f"{plan.slug}-title")
        + tag("desc", plain(desc), id=f"{plan.slug}-desc")
        + tag("style", css.replace("&", "&amp;").replace("<", "&lt;"))
        + under
        + figure
        + over
    )
    return (
        tag(
            "svg",
            body,
            xmlns="http://www.w3.org/2000/svg",
            viewBox=f"0 0 {plan.width} {plan.height}",
            width=plan.width,
            height=plan.height,
            class_=f"chr-a chr-a-{plan.slug}",
            role="img",
            aria_labelledby=f"{plan.slug}-title {plan.slug}-desc",
            data_theme=None if plan.theme_mode == "auto" else plan.theme_mode,
        )
        + "\n"
    )
