"""Inline diagrams: Claude-drawn SVG, rebuilt from an allowlist so the page stays safe.

A diagram explains a mechanism (an order's path, a system's parts, a process) in the
page's own type and colors: classes such as `box`, `line`, `f-accent` or `s-legacy`
map to theme tokens. Anything outside the allowlist is an error, never silently kept.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Callable
from dataclasses import dataclass, field

from chronicle.core.story.html import tag

ELEMENTS = {
    "svg",
    "g",
    "path",
    "rect",
    "circle",
    "ellipse",
    "line",
    "polyline",
    "polygon",
    "text",
    "tspan",
    "title",
    "desc",
    "defs",
    "marker",
    "linearGradient",
    "stop",
    "use",
    "symbol",
}
ATTRS = {
    "id",
    "class",
    "d",
    "x",
    "y",
    "x1",
    "y1",
    "x2",
    "y2",
    "cx",
    "cy",
    "r",
    "rx",
    "ry",
    "dx",
    "dy",
    "width",
    "height",
    "points",
    "transform",
    "viewBox",
    "fill",
    "stroke",
    "stroke-width",
    "stroke-dasharray",
    "stroke-linecap",
    "stroke-linejoin",
    "opacity",
    "fill-opacity",
    "stroke-opacity",
    "font-size",
    "font-weight",
    "font-style",
    "text-anchor",
    "dominant-baseline",
    "letter-spacing",
    "offset",
    "stop-color",
    "stop-opacity",
    "markerWidth",
    "markerHeight",
    "refX",
    "refY",
    "orient",
    "markerUnits",
    "marker-start",
    "marker-mid",
    "marker-end",
    "href",
    "preserveAspectRatio",
    "data-tip",
}
_REF = re.compile(r"^url\(#([\w.-]+)\)$")
_ID = re.compile(r"^[A-Za-z][\w.-]{0,60}$")
_SAFE_VALUE = re.compile(r"^[^<>\"`]*$")
_PLAIN_COLOR = re.compile(r"^(none|currentColor|transparent|#[0-9a-fA-F]{3,8}|[a-z]{3,20})$")


class DiagramError(ValueError):
    """A diagram the sanitizer will not pass, with what to change."""


@dataclass
class Diagram:
    """Sanitized SVG markup plus the ids the steps may focus."""

    markup: str
    width: float
    height: float
    ids: set[str] = field(default_factory=set)
    tips: int = 0


def sanitize(text: str, prefix: str, fill_text: Callable[[str], str] | None = None) -> Diagram:
    """Rebuild SVG from allowed elements and attributes; ids gain `prefix-` to stay unique."""
    if "<!DOCTYPE" in text or "<!ENTITY" in text:
        raise DiagramError("remove the DOCTYPE and entity declarations from the diagram")
    try:
        root = ET.fromstring(text)  # noqa: S314 - DOCTYPE and ENTITY are rejected above, so no entity expansion reaches expat
    except ET.ParseError as exc:
        raise DiagramError(f"the diagram is not well-formed XML: {exc}") from exc
    if _local(root.tag) != "svg":
        raise DiagramError("the diagram's root element must be <svg>")
    box = [float(v) for v in re.findall(r"-?[\d.]+", root.get("viewBox", ""))]
    if len(box) != 4 or box[2] <= 0 or box[3] <= 0:
        raise DiagramError("the diagram needs a viewBox, such as viewBox='0 0 960 420'")
    ids = {str(el.get("id")) for el in root.iter() if el.get("id")}
    for i in ids:
        if not _ID.match(i):
            raise DiagramError(f"id {i!r} must start with a letter and use letters, digits, - or _")
    out = Diagram("", box[2], box[3])
    out.markup = _node(root, prefix, ids, out, fill_text or (lambda s: s), top=True)
    out.ids = ids
    return out


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1]


def _node(
    el: ET.Element,
    prefix: str,
    ids: set[str],
    out: Diagram,
    fill_text: Callable[[str], str],
    top: bool = False,
) -> str:
    name = _local(el.tag)
    if name not in ELEMENTS:
        raise DiagramError(
            f"<{name}> is not allowed in a diagram; use {', '.join(sorted(ELEMENTS))}"
        )
    attrs: dict[str, str | bool | None] = {}
    for raw_key, value in el.attrib.items():
        key = _local(raw_key)
        if key not in ATTRS:
            raise DiagramError(f"attribute {key!r} on <{name}> is not allowed; style with classes")
        attrs[key.replace("-", "_") if key != "viewBox" else key] = _value(
            key, value, prefix, ids, name
        )
    if el.get("data-tip"):
        out.tips += 1
        attrs["data_tip"] = fill_text(str(el.get("data-tip")))
        attrs["tabindex"] = "0"
        attrs["role"] = "button"
    if top:
        attrs = {"viewBox": str(attrs.get("viewBox")), "class_": "dg-svg"}
    elif "class" in attrs:
        attrs["class_"] = attrs.pop("class")
    inner = ""
    if el.text and el.text.strip() and name in ("text", "tspan", "title", "desc"):
        inner += _escape(fill_text(el.text))
    for child in el:
        inner += _node(child, prefix, ids, out, fill_text)
        if child.tail and child.tail.strip() and name in ("text", "tspan"):
            inner += _escape(fill_text(child.tail))
    return tag(name, inner, **attrs)


def _value(key: str, value: str, prefix: str, ids: set[str], name: str) -> str:
    v = value.strip()
    if not _SAFE_VALUE.match(v) or "javascript" in v.lower() or "expression" in v.lower():
        raise DiagramError(f"{key}={value!r} on <{name}> has characters a diagram may not use")
    if key == "id":
        return f"{prefix}-{v}"
    if key == "href":
        if not v.startswith("#") or v[1:] not in ids:
            raise DiagramError(f"href {v!r} must point at an id in this diagram")
        return f"#{prefix}-{v[1:]}"
    ref = _REF.match(v)
    if ref:
        if ref.group(1) not in ids:
            raise DiagramError(f"{key}={v!r} points at an id that is not in this diagram")
        return f"url(#{prefix}-{ref.group(1)})"
    if key in ("fill", "stroke", "stop-color") and not _PLAIN_COLOR.match(v):
        raise DiagramError(f"{key}={v!r}: use a #hex color, none, or a class such as f-accent")
    return v


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
