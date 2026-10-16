"""Paint a parsed SVG drawing in ink and watercolor.

Each filled shape becomes a transparent wash that sits slightly loose of its outline,
darkens at the rim, granulates in the paper and grades toward the shadow side; each
stroke becomes a dip-pen line. Shapes are painted in document order and a filled shape
covers what is under it, so the drawing reads like the SVG it came from.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

import numpy as np

from chronicle.core.watercolor.canvas import Canvas, ColorRamp
from chronicle.core.watercolor.scene import Layer, Painting, SceneError
from chronicle.core.watercolor.svg.parse import Drawing, Item, SvgError, parse, to_hex

VIGNETTES = ("deckle", "soft", "spot", "none")


@dataclass(frozen=True)
class Style:
    """Scene-wide brush settings; every field can be overridden per shape with data-*."""

    light: float = 225.0  # where the light comes from, degrees (x right, y down): upper left
    shade: float = 0.35
    loose: float = 1.0
    wet: float = 0.0
    edge: float = 0.45
    grain: float = 0.24
    flow: float = 0.32
    opacity: float = 0.86
    line: float = 1.0
    jitter: float = 0.55
    blooms: int = 0

    @classmethod
    def from_spec(cls, spec: Mapping[str, Any]) -> Style:
        known = {f: getattr(cls, f) for f in cls.__dataclass_fields__}
        unknown = sorted(set(spec) - set(known))
        if unknown:
            raise SceneError(f"style has no setting {', '.join(unknown)}; use {', '.join(known)}")
        values: dict[str, Any] = {}
        for key, value in spec.items():
            try:
                values[key] = type(known[key])(value)
            except (TypeError, ValueError) as exc:
                raise SceneError(f"style.{key} must be a number") from exc
        return cls(**values)


def paint_drawing(
    drawing: Drawing,
    *,
    seed: int = 1,
    scale: float = 1.0,
    vignette: str = "soft",
    style: Style | None = None,
    underlay: Canvas | None = None,
) -> Painting:
    """Paint every item; layers go on their own sheets so the page can move them."""
    if vignette not in VIGNETTES:
        raise SceneError(f"unknown vignette {vignette!r}; use one of {', '.join(VIGNETTES)}")
    st = style or Style()
    canvas = underlay or Canvas(drawing.width, drawing.height, seed=seed, scale=scale)
    for item in drawing.items:
        paint_item(canvas, item, st)
    painting = Painting(drawing.width, drawing.height, canvas.finish(vignette))
    for k, spec in enumerate(drawing.layers):
        sheet = Canvas(
            drawing.width, drawing.height, seed=seed + 211 + k, scale=scale, paper=canvas.paper
        )
        for item in spec.items:
            paint_item(sheet, item, st)
        opaque = spec.motion in ("cross", "rise", "descend", "bob", "sway", "spin", "pop")
        image, box = sheet.sprite(opaque=opaque)
        if box is not None:
            painting.layers.append(
                Layer(
                    spec.name,
                    image,
                    box,
                    motion=spec.motion,
                    travel=spec.travel,
                    blend="normal" if opaque else "multiply",
                )
            )
    painting.anchors.update(drawing.anchors)
    painting.labels.extend(
        {
            "x": round(lab.x, 1),
            "y": round(lab.y, 1),
            "text": lab.text,
            "size": round(lab.size, 1),
            "anchor": lab.anchor,
            "angle": round(lab.angle, 1),
            "style": lab.style,
            "color": lab.color,
            "weight": lab.weight,
        }
        for lab in drawing.labels
    )
    return painting


def _hint(item: Item, key: str, default: float) -> float:
    raw = item.hints.get(key)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise SvgError(f"data-{key}={raw!r} on {item.name or 'a shape'} must be a number") from exc


def _size(points: np.ndarray) -> float:
    span = points.max(axis=0) - points.min(axis=0)
    return float(min(span[0], span[1]))


def paint_item(c: Canvas, item: Item, st: Style) -> None:
    """Fill then stroke one shape."""
    paint = item.hints.get("paint", "wash")
    closed = [np.asarray(s.points, dtype=np.float64) for s in item.subpaths if len(s.points) >= 3]
    if item.fill is not None and paint != "none" and closed:
        _fill(c, item, st, paint, closed)
    hatch = _hint(item, "hatch", 0.0)
    if hatch > 0 and closed:
        _hatch(c, closed, hatch, st, item)
    line = item.hints.get("line", "ink")
    if item.stroke is not None and line != "none" and item.stroke_width > 0:
        for sub in item.subpaths:
            pts = np.asarray(sub.points, dtype=np.float64)
            if len(pts) < 2:
                continue
            if line == "pencil":
                c.pencil(pts, closed=sub.closed, opacity=0.5 * item.stroke_opacity)
                continue
            overshoot = 0.0 if line == "lift" else _hint(item, "overshoot", 1.0)
            for run, is_closed in _runs(pts, sub.closed, c.rng, overshoot):
                c.ink(
                    run,
                    width=item.stroke_width * st.line,
                    pigment=to_hex(item.stroke),
                    opacity=min(1.0, 0.92 * item.stroke_opacity),
                    jitter=_hint(item, "jitter", st.jitter),
                    taper=0.0 if is_closed else 0.1,
                    breaks=0.45 if item.dashed else _hint(item, "breaks", 0.0),
                    closed=is_closed,
                    lift=line == "lift",
                )


def _runs(
    pts: np.ndarray, closed: bool, rng: np.random.Generator, overshoot: float
) -> list[tuple[np.ndarray, bool]]:
    """Split an outline at its sharp corners into separate pen strokes.

    Each stroke runs a little past its corner, as a quick hand draws a box: the overlap
    is what makes a ruled shape read as drawn rather than plotted.
    """
    n = len(pts)
    if n < 3 or overshoot <= 0:
        return [(pts, closed)]
    ring = pts if closed else pts[1:-1]
    prev = np.roll(pts, 1, axis=0) if closed else pts[:-2]
    nxt = np.roll(pts, -1, axis=0) if closed else pts[2:]
    v1, v2 = ring - prev, nxt - ring
    turn = np.abs(np.arctan2(v1[:, 0] * v2[:, 1] - v1[:, 1] * v2[:, 0], (v1 * v2).sum(axis=1)))
    corners = np.nonzero(turn > math.radians(38))[0]
    if not closed:
        corners = corners + 1
    if len(corners) == 0 or (closed and len(corners) < 2):
        return [(pts, closed)]
    cuts = list(corners)
    if not closed:
        cuts = [0, *cuts, n - 1]
    runs: list[tuple[np.ndarray, bool]] = []
    pairs = list(zip(cuts, cuts[1:], strict=False))
    if closed:
        pairs.append((cuts[-1], cuts[0] + n))
    loop = np.vstack([pts, pts]) if closed else pts
    for a, b in pairs:
        run = loop[a : b + 1].copy()
        if len(run) < 2:
            continue
        for end, inner in ((0, 1), (-1, -2)):
            if not closed and ((end == 0 and a == 0) or (end == -1 and b == n - 1)):
                continue
            direction = run[end] - run[inner]
            length = float(np.hypot(*direction))
            if length < 1e-6 or rng.random() > 0.7:
                continue
            reach = min(9.0, 0.05 * _length(run)) * overshoot * float(rng.uniform(0.4, 1.2))
            run[end] = run[end] + direction / length * reach
        runs.append((run, False))
    return runs


def _hatch(c: Canvas, polys: list[np.ndarray], amount: float, st: Style, item: Item) -> None:
    """Pen hatching across a shape, for shadow without a darker wash."""
    stack = np.vstack(polys)
    angle = math.radians(st.light - 180 + 90 + 30)
    ux, uy = math.cos(angle), math.sin(angle)  # along the strokes
    nx, ny = -uy, ux  # across them
    spacing = max(3.0, 11.0 - 7.0 * min(amount, 1.0))
    across = stack @ np.array([nx, ny])
    color = to_hex(item.stroke) if item.stroke is not None else "#2b231d"
    for offset in np.arange(float(across.min()) + spacing / 2, float(across.max()), spacing):
        crossings: list[float] = []
        for poly in polys:
            ring = np.vstack([poly, poly[:1]])
            d = ring @ np.array([nx, ny]) - offset
            along = ring @ np.array([ux, uy])
            for i in range(len(ring) - 1):
                if (d[i] < 0) != (d[i + 1] < 0):
                    f = d[i] / (d[i] - d[i + 1])
                    crossings.append(float(along[i] + f * (along[i + 1] - along[i])))
        crossings.sort()
        for a, b in zip(crossings[::2], crossings[1::2], strict=False):
            if b - a < 6:
                continue
            trim = (b - a) * float(c.rng.uniform(0.03, 0.12))
            start = np.array([nx, ny]) * offset + np.array([ux, uy]) * (a + trim)
            end = np.array([nx, ny]) * offset + np.array([ux, uy]) * (b - trim)
            c.ink(np.vstack([start, end]), width=0.9, pigment=color, opacity=0.55, jitter=0.4)


def _length(run: np.ndarray) -> float:
    return float(np.hypot(*np.diff(run, axis=0).T).sum())


def _fill(c: Canvas, item: Item, st: Style, paint: str, polys: list[np.ndarray]) -> None:
    if item.fill is None:
        return
    size = max(_size(np.vstack(polys)), 1.0)
    wet = _hint(item, "wet", 0.55 if paint == "wet" else st.wet)
    if paint == "reserve":
        c.reserve(polys, softness=wet)
        return
    color = to_hex(item.fill)
    if paint == "dry":
        c.drybrush(polys, color, opacity=0.7 * item.fill_opacity, angle=st.light - 180)
        return
    glaze = paint == "glaze" or item.fill_opacity < 0.95
    loose = _hint(item, "loose", st.loose)
    polys = _loosen(polys, c.rng, loose, size)
    shade = _hint(item, "shade", st.shade)
    away = st.light - 180.0
    gradient = (away, 1.0 - 0.32 * shade, 1.0 + 0.22 * shade) if shade > 0 else None
    ramp: ColorRamp | None = None
    if item.gradient is not None:
        g = item.gradient
        ramp = (g.p0, g.p1, [(o, rgb, a) for o, rgb, a in g.stops])
    base = 0.55 if paint == "glaze" else st.opacity
    c.wash(
        polys,
        color,
        opacity=base * item.fill_opacity,
        edge=_hint(item, "edge", st.edge if paint != "wet" else 0.15),
        wet=wet,
        granulation=_hint(item, "grain", st.grain),
        flow=st.flow,
        wobble_px=min(1.8, 0.035 * size),
        blooms=int(_hint(item, "blooms", st.blooms)),
        gradient=gradient,
        occlude=not glaze,
        evenodd=len(polys) > 1,
        ramp=ramp,
    )


def _loosen(
    polys: list[np.ndarray], rng: np.random.Generator, loose: float, size: float
) -> list[np.ndarray]:
    """Shift and swell a wash a little off its outline, the way a quick brush lands."""
    if loose <= 0:
        return polys
    reach = min(4.0, max(0.6, 0.014 * size)) * loose
    angle = float(rng.uniform(0, 2 * math.pi))
    shift = np.array([math.cos(angle), math.sin(angle)]) * reach
    out = []
    for poly in polys:
        center = poly.mean(axis=0)
        grow = 1.0 + 0.6 * reach / max(size, 1.0)
        out.append((poly - center) * grow + center + shift)
    return out


def paint_scene(spec: Mapping[str, Any], text: str, scale: float = 1.0) -> Painting:
    """Paint a story scene drawn as SVG: {"svg": file, "seed", "vignette", "style", "width"}."""
    width = spec.get("width")
    drawing = parse(text, int(width) if width else None)
    return paint_drawing(
        drawing,
        seed=int(spec.get("seed", 1)),
        scale=scale,
        vignette=str(spec.get("vignette", "soft")),
        style=Style.from_spec(dict(spec.get("style", {}))),
    )
