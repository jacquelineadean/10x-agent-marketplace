"""Read an illustration written as SVG into paintable items.

Claude draws a scene as plain SVG (shapes, paths, groups, transforms, linear gradients)
and the painter renders it in ink and watercolor. Painter hints ride on `data-*`
attributes, so the same file still opens in any SVG viewer:

    data-paint   wash (default), glaze, wet, dry, reserve, none
    data-line    ink (default), pencil, lift (a highlight scrubbed back to paper), none
    data-shade   0 to 1: how much darker a wash gets on the side away from the light
    data-wet, data-edge, data-blooms, data-loose, data-grain: wash texture
    data-layer   paint this group on its own sheet; data-motion and data-travel move it
    data-anchor  name a point (the element's center) for hotspots and overlay marks
    <text>       becomes live overlay text in the page's fonts, never painted

Standard library only: the parser runs and is tested without NumPy.
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping
from dataclasses import dataclass, field

from chronicle.core.watercolor.pigments import PIGMENTS
from chronicle.core.watercolor.svg import pathdata as pd
from chronicle.core.watercolor.svg.pathdata import IDENTITY, Matrix, PathError, Point

RGB = tuple[float, float, float]
MOTIONS = ("none", "descend", "drift", "fall", "cross", "rise", "sway", "bob", "pop", "spin")
PAINTS = ("wash", "glaze", "wet", "dry", "reserve", "none")
LINES = ("ink", "pencil", "lift", "none")
LABEL_STYLES = ("hand", "label", "caption", "display", "mono", "number")
SHAPES = ("path", "rect", "circle", "ellipse", "line", "polyline", "polygon")
CONTAINERS = ("svg", "g", "a")
SKIPPED = ("title", "desc", "metadata", "defs", "style", "linearGradient", "radialGradient", "stop")
INHERITED = (
    "fill",
    "stroke",
    "stroke-width",
    "fill-opacity",
    "stroke-opacity",
    "stroke-dasharray",
    "font-size",
    "font-weight",
    "text-anchor",
    "data-paint",
    "data-line",
    "data-shade",
    "data-wet",
    "data-edge",
    "data-blooms",
    "data-loose",
    "data-grain",
    "data-label",
)
NAMED = {
    "black": "#000000",
    "white": "#ffffff",
    "red": "#ff0000",
    "green": "#008000",
    "blue": "#0000ff",
    "yellow": "#ffff00",
    "orange": "#ffa500",
    "gray": "#808080",
    "grey": "#808080",
    "brown": "#a52a2a",
    "tan": "#d2b48c",
    "navy": "#000080",
    "teal": "#008080",
    "maroon": "#800000",
    "silver": "#c0c0c0",
    "beige": "#f5f5dc",
    "ivory": "#fffff0",
    "khaki": "#f0e68c",
    "salmon": "#fa8072",
    "gold": "#ffd700",
    "crimson": "#dc143c",
    "skyblue": "#87ceeb",
    "slategray": "#708090",
    "wheat": "#f5deb3",
}
_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
_RGB = re.compile(r"^rgb\(\s*([\d.]+%?)\s*,?\s*([\d.]+%?)\s*,?\s*([\d.]+%?)\s*\)$")
_URL = re.compile(r"^url\(\s*#([\w.-]+)\s*\)$")
_NAME = re.compile(r"^[A-Za-z][\w-]{0,40}$")


class SvgError(ValueError):
    """An illustration that cannot be painted, with a message that says what to change."""


@dataclass
class Gradient:
    """A linear gradient in drawing coordinates: color stops along the line p0 to p1."""

    p0: Point
    p1: Point
    stops: list[tuple[float, RGB, float]]


@dataclass
class Item:
    """One SVG shape: its outline in drawing pixels and how to paint it."""

    subpaths: list[pd.Subpath]
    fill: RGB | None = None
    fill_opacity: float = 1.0
    gradient: Gradient | None = None
    stroke: RGB | None = None
    stroke_opacity: float = 1.0
    stroke_width: float = 1.0
    dashed: bool = False
    hints: dict[str, str] = field(default_factory=dict)
    name: str = ""


@dataclass
class Label:
    """Overlay text: placed in drawing pixels, set in the page's fonts."""

    x: float
    y: float
    text: str
    size: float
    anchor: str = "start"
    angle: float = 0.0
    style: str = "hand"
    color: str = ""
    weight: str = ""


@dataclass
class LayerSpec:
    name: str
    motion: str
    travel: float
    items: list[Item] = field(default_factory=list)


@dataclass
class Drawing:
    """A parsed illustration at its painted size."""

    width: int
    height: int
    items: list[Item] = field(default_factory=list)
    layers: list[LayerSpec] = field(default_factory=list)
    anchors: dict[str, Point] = field(default_factory=dict)
    labels: list[Label] = field(default_factory=list)


def parse_color(value: str | None) -> RGB | None | str:
    """A fill or stroke value as RGB; None for none; 'url:<id>' for a gradient reference."""
    if value is None:
        return None
    v = value.strip()
    if v in ("", "none", "transparent"):
        return None
    if v == "currentColor":
        v = "#2b231d"
    url = _URL.match(v)
    if url:
        return f"url:{url.group(1)}"
    v = PIGMENTS.get(v, v)
    v = NAMED.get(v.lower(), v)
    if _HEX.match(v):
        hexes = v[1:]
        if len(hexes) == 3:
            hexes = "".join(c * 2 for c in hexes)
        return (int(hexes[0:2], 16) / 255, int(hexes[2:4], 16) / 255, int(hexes[4:6], 16) / 255)
    rgb = _RGB.match(v)
    if rgb:
        parts = []
        for part in rgb.groups():
            n = float(part.rstrip("%"))
            parts.append(n / 100 if part.endswith("%") else n / 255)
        return (min(parts[0], 1.0), min(parts[1], 1.0), min(parts[2], 1.0))
    raise SvgError(f"cannot read color {value!r}; use #rrggbb, rgb(), a pigment name or none")


def to_hex(rgb: RGB) -> str:
    return "#" + "".join(f"{round(max(0.0, min(1.0, c)) * 255):02x}" for c in rgb)


def _style(el: ET.Element) -> dict[str, str]:
    props = {k: v for k, v in el.attrib.items() if "}" not in k}
    for decl in props.pop("style", "").split(";"):
        if ":" in decl:
            key, value = decl.split(":", 1)
            props[key.strip()] = value.strip()
    return props


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _float(props: Mapping[str, str], key: str, default: float = 0.0) -> float:
    raw = props.get(key)
    if raw is None or raw == "":
        return default
    found = pd.numbers(raw)
    if not found:
        raise SvgError(f"{key}={raw!r} is not a number")
    return found[0]


class _Reader:
    def __init__(self, root: ET.Element, width: float, height: float, base: Matrix) -> None:
        self.ids: dict[str, ET.Element] = {}
        for el in root.iter():
            if el.get("id"):
                self.ids[str(el.get("id"))] = el
        self.drawing = Drawing(round(width), round(height))
        self.base = base
        self.depth = 0

    def walk(
        self,
        el: ET.Element,
        m: Matrix,
        inherited: dict[str, str],
        opacity: float,
        layer: LayerSpec | None,
    ) -> None:
        name = _local(el.tag)
        if name in SKIPPED:
            return
        props = _style(el)
        if props.get("display") == "none" or props.get("visibility") == "hidden":
            return
        try:
            m = pd.multiply(m, pd.parse_transform(props.get("transform")))
        except PathError as exc:
            raise SvgError(str(exc)) from exc
        style = dict(inherited)
        for key in INHERITED:
            if key in props:
                style[key] = props[key]
        opacity *= _float(props, "opacity", 1.0)
        if props.get("data-anchor"):
            self._anchor(el, name, props, m)
        if props.get("data-layer"):
            if layer is not None:
                raise SvgError(f"layer {props['data-layer']!r} is inside another layer")
            layer = self._layer(props)
        if name in CONTAINERS:
            for child in el:
                self.walk(child, m, style, opacity, layer)
        elif name == "use":
            self._use(el, props, m, style, opacity, layer)
        elif name == "text":
            self._text(el, props, m, style)
        elif name in SHAPES:
            item = self._item(name, props, m, style, opacity)
            if item is not None:
                (layer.items if layer else self.drawing.items).append(item)
        else:
            raise SvgError(
                f"<{name}> is not supported; draw with {', '.join(SHAPES)}, g, use and text"
            )

    def _layer(self, props: Mapping[str, str]) -> LayerSpec:
        name = props["data-layer"]
        if not _NAME.match(name):
            raise SvgError(f"layer name {name!r} must be letters, digits, - or _")
        if any(existing.name == name for existing in self.drawing.layers):
            raise SvgError(f"layer {name!r} is used twice")
        motion = props.get("data-motion", "none")
        if motion not in MOTIONS:
            raise SvgError(f"data-motion {motion!r} must be one of {', '.join(MOTIONS)}")
        travel = _float(props, "data-travel", 0.0) * pd.scale_of(self.base)
        spec = LayerSpec(name, motion, travel)
        self.drawing.layers.append(spec)
        return spec

    def _anchor(self, el: ET.Element, name: str, props: Mapping[str, str], m: Matrix) -> None:
        key = props["data-anchor"]
        if not _NAME.match(key):
            raise SvgError(f"anchor name {key!r} must be letters, digits, - or _")
        points: list[Point] = []
        if name in SHAPES:
            for sub in self._outline(name, props, m, 3.0):
                points.extend(sub.points)
        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            point = ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)
        else:
            point = pd.apply(m, (_float(props, "x"), _float(props, "y")))
        self.drawing.anchors[key] = point

    def _use(
        self,
        el: ET.Element,
        props: Mapping[str, str],
        m: Matrix,
        style: dict[str, str],
        opacity: float,
        layer: LayerSpec | None,
    ) -> None:
        href = props.get("href") or el.get("{http://www.w3.org/1999/xlink}href") or ""
        target = self.ids.get(href[1:]) if href.startswith("#") else None
        if target is None:
            raise SvgError(f"<use href={href!r}> must point at an element id in this drawing")
        self.depth += 1
        if self.depth > 8:
            raise SvgError("<use> nests more than 8 deep; check for a reference loop")
        offset = (1.0, 0.0, 0.0, 1.0, _float(props, "x"), _float(props, "y"))
        name = _local(target.tag)
        if name in ("symbol", "defs"):
            for child in target:
                self.walk(child, pd.multiply(m, offset), style, opacity, layer)
        else:
            self.walk(target, pd.multiply(m, offset), style, opacity, layer)
        self.depth -= 1

    def _text(
        self, el: ET.Element, props: Mapping[str, str], m: Matrix, style: dict[str, str]
    ) -> None:
        text = " ".join("".join(el.itertext()).split())
        if not text:
            return
        x, y = pd.apply(m, (_float(props, "x"), _float(props, "y")))
        size = _float(style, "font-size", 28.0) * pd.scale_of(m)
        angle = 0.0
        a, b = m[0], m[1]
        if abs(b) > 1e-6:
            angle = math.degrees(math.atan2(b, a))
        kind = style.get("data-label", "hand")
        if kind not in LABEL_STYLES:
            raise SvgError(f"data-label {kind!r} must be one of {', '.join(LABEL_STYLES)}")
        color = parse_color(style.get("fill", "#2b231d"))
        anchor = style.get("text-anchor", "start")
        self.drawing.labels.append(
            Label(
                x=x,
                y=y,
                text=text,
                size=size,
                anchor=anchor if anchor in ("start", "middle", "end") else "start",
                angle=angle,
                style=kind,
                color=to_hex(color) if isinstance(color, tuple) else "",
                weight=style.get("font-weight", ""),
            )
        )

    def _outline(
        self, name: str, props: Mapping[str, str], m: Matrix, step: float
    ) -> list[pd.Subpath]:
        local_step = step / pd.scale_of(m)
        try:
            if name == "path":
                subs = pd.parse_path(props.get("d", ""), local_step)
            elif name == "rect":
                w, h = _float(props, "width"), _float(props, "height")
                if w <= 0 or h <= 0:
                    return []
                rx = _float(props, "rx", -1.0)
                ry = _float(props, "ry", -1.0)
                rx, ry = (ry if rx < 0 else rx), (rx if ry < 0 else ry)
                pts = pd.rect_points(
                    _float(props, "x"), _float(props, "y"), w, h, max(rx, 0), max(ry, 0), local_step
                )
                subs = [pd.Subpath(pts, True)]
            elif name in ("circle", "ellipse"):
                rx = _float(props, "r") if name == "circle" else _float(props, "rx")
                ry = _float(props, "r") if name == "circle" else _float(props, "ry")
                if rx <= 0 or ry <= 0:
                    return []
                pts = pd.ellipse_points(
                    _float(props, "cx"), _float(props, "cy"), rx, ry, local_step
                )
                subs = [pd.Subpath(pts, True)]
            elif name == "line":
                pts = [
                    (_float(props, "x1"), _float(props, "y1")),
                    (_float(props, "x2"), _float(props, "y2")),
                ]
                subs = [pd.Subpath(pts, False)]
            else:
                values = pd.numbers(props.get("points"))
                pts = [(values[i], values[i + 1]) for i in range(0, len(values) - 1, 2)]
                subs = [pd.Subpath(pts, name == "polygon")] if len(pts) >= 2 else []
        except PathError as exc:
            raise SvgError(f"<{name}>: {exc}") from exc
        return [pd.Subpath(pd.transform_points(m, s.points), s.closed) for s in subs]

    def _item(
        self, name: str, props: Mapping[str, str], m: Matrix, style: dict[str, str], opacity: float
    ) -> Item | None:
        subs = self._outline(name, props, m, 3.0)
        if not subs:
            return None
        fill_value = parse_color(style.get("fill", "#000000") if name != "line" else "none")
        stroke_value = parse_color(style.get("stroke"))
        gradient = None
        if isinstance(fill_value, str):
            gradient = self._gradient(fill_value[4:], subs)
            fill_value = gradient.stops[0][1]
        if isinstance(stroke_value, str):
            stroke_value = self._gradient(stroke_value[4:], subs).stops[0][1]
        for key, allowed in (("data-paint", PAINTS), ("data-line", LINES)):
            if key in style and style[key] not in allowed:
                raise SvgError(f"{key}={style[key]!r} must be one of {', '.join(allowed)}")
        hints = {k[5:]: v for k, v in style.items() if k.startswith("data-")}
        return Item(
            subpaths=subs,
            fill=fill_value,
            fill_opacity=opacity * _float(style, "fill-opacity", 1.0),
            gradient=gradient,
            stroke=stroke_value,
            stroke_opacity=opacity * _float(style, "stroke-opacity", 1.0),
            stroke_width=_float(style, "stroke-width", 1.0) * pd.scale_of(m),
            dashed=bool(style.get("stroke-dasharray", "none") not in ("none", "")),
            hints=hints,
            name=str(props.get("id", "")),
        )

    def _gradient(self, gid: str, subs: list[pd.Subpath]) -> Gradient:
        el = self.ids.get(gid)
        if el is None or _local(el.tag) != "linearGradient":
            raise SvgError(f"fill url(#{gid}) must name a linearGradient in this drawing")
        stops: list[tuple[float, RGB, float]] = []
        for stop in el:
            if _local(stop.tag) != "stop":
                continue
            sp = _style(stop)
            raw = sp.get("offset", "0")
            offset = float(raw.rstrip("%")) / (100 if raw.endswith("%") else 1)
            color = parse_color(sp.get("stop-color", "#000000"))
            if not isinstance(color, tuple):
                raise SvgError(f"gradient #{gid} needs plain stop colors")
            stops.append((offset, color, _float(sp, "stop-opacity", 1.0)))
        if not stops:
            raise SvgError(f"gradient #{gid} has no stops")
        xs = [p[0] for s in subs for p in s.points]
        ys = [p[1] for s in subs for p in s.points]
        box = (min(xs), min(ys), max(xs), max(ys))
        gp = _style(el)

        def frac(key: str, default: str, lo: float, span: float) -> float:
            raw = gp.get(key, default)
            value = float(raw.rstrip("%")) / (100 if raw.endswith("%") else 1)
            return lo + value * span

        if gp.get("gradientUnits") == "userSpaceOnUse":
            raise SvgError(f"gradient #{gid}: use the default objectBoundingBox units")
        w, h = box[2] - box[0], box[3] - box[1]
        p0 = (frac("x1", "0", box[0], w), frac("y1", "0", box[1], h))
        p1 = (frac("x2", "1", box[0], w), frac("y2", "0", box[1], h))
        return Gradient(p0, p1, sorted(stops, key=lambda s: s[0]))


def parse(text: str, width: int | None = None) -> Drawing:
    """Parse SVG text. The drawing is scaled so its painted width is `width` (default: 1600
    when the viewBox is narrower than 1000, else the viewBox width)."""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise SvgError("remove the DOCTYPE and entity declarations from the drawing")
    try:
        root = ET.fromstring(text)  # noqa: S314 - DOCTYPE and ENTITY are rejected above, so no entity expansion reaches expat
    except ET.ParseError as exc:
        raise SvgError(f"the drawing is not well-formed XML: {exc}") from exc
    if _local(root.tag) != "svg":
        raise SvgError("the drawing's root element must be <svg>")
    box = pd.numbers(root.get("viewBox"))
    if len(box) != 4:
        w0, h0 = _float(root.attrib, "width"), _float(root.attrib, "height")
        box = [0.0, 0.0, w0, h0]
    min_x, min_y, vb_w, vb_h = box
    if vb_w <= 0 or vb_h <= 0:
        raise SvgError("the drawing needs a viewBox such as viewBox='0 0 1600 1000'")
    target = width or (1600 if vb_w < 1000 else vb_w)
    k = target / vb_w
    out_w, out_h = vb_w * k, vb_h * k
    if not (200 <= out_w <= 3200 and 120 <= out_h <= 3200):
        raise SvgError(f"painted size {out_w:.0f}x{out_h:.0f} is outside 200x120 to 3200x3200")
    base: Matrix = (k, 0.0, 0.0, k, -min_x * k, -min_y * k)
    reader = _Reader(root, out_w, out_h, base)
    reader.walk(root, base, {}, 1.0, None)
    if not reader.drawing.items and not reader.drawing.layers:
        raise SvgError("the drawing has no shapes to paint")
    return reader.drawing


__all__ = ["IDENTITY", "Drawing", "Item", "Label", "LayerSpec", "SvgError", "parse", "to_hex"]
