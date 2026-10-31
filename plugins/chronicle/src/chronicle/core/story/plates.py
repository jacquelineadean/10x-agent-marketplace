"""Plates: the painter's images on a story page, with moving layers, labels and hotspots.

chronicle's art provider draws these for `hero.art`, `chapters[].art` and the `plate` block.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag, void
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder


def plate(b: Builder, key: str, caption: Any = "", width: str = "wide", spots: Any = None) -> str:
    """A painting: base image, moving layers, an overlay for lines, optional hotspots."""
    entry = b.manifest.get(key)
    if not entry:
        return ""
    scene = b.story.get("art", {}).get(key, {})
    w, h = int(entry["width"]), int(entry["height"])
    b.art_files.append(str(entry["file"]))
    layers = "".join(_layer(b, layer, w, h) for layer in entry.get("layers", []))
    anchors = entry.get("anchors", {})
    fid = b.register(
        {
            "type": "plate",
            "art": key,
            "width": w,
            "height": h,
            "anchors": anchors,
            "spots": spots or [],
        }
    )
    spot_html, cards = _spots(b, spots or [], anchors, w, h)
    base = void(
        "img",
        class_="base",
        src=str(entry["file"]),
        alt=str(scene.get("alt", "")),
        width=w,
        height=h,
        decoding="async",
    )
    overlay = tag(
        "svg",
        "".join(_label(b, lab) for lab in entry.get("labels", [])),
        class_="overlay",
        viewBox=f"0 0 {w} {h}",
        preserveAspectRatio="none",
        aria_hidden="true",
    )
    stage = tag(
        "div",
        base + layers + overlay + spot_html,
        class_="stage develop",
        style=f"aspect-ratio:{w}/{h}",
    )
    cap = tag("figcaption", b.inline(caption)) if caption else ""
    cls = "plate wide" if width == "wide" else "plate inset"
    return tag("figure", tag("div", stage, class_="frame") + cap + cards, class_=cls, data_fig=fid)


def _label(b: Builder, lab: Mapping[str, Any]) -> str:
    """Overlay text drawn in the SVG, set live in the theme's fonts."""
    angle = float(lab.get("angle", 0))
    x, y = float(lab["x"]), float(lab["y"])
    return tag(
        "text",
        plain(str(b.plain_text(str(lab.get("text", ""))))),
        x=f"{x:.1f}",
        y=f"{y:.1f}",
        class_=f"lbl lbl-{lab.get('style', 'hand')}",
        font_size=f"{float(lab.get('size', 28)):.1f}",
        text_anchor=str(lab.get("anchor", "start")),
        fill=str(lab.get("color") or "") or None,
        font_weight=str(lab.get("weight") or "") or None,
        transform=f"rotate({angle:.1f} {x:.1f} {y:.1f})" if abs(angle) > 0.05 else None,
    )


def _layer(b: Builder, layer: Mapping[str, Any], w: int, h: int) -> str:
    b.art_files.append(str(layer["file"]))
    x, y, lw, lh = layer["box"]
    style = (
        f"left:{100 * x / w:.3f}%;top:{100 * y / h:.3f}%;"
        f"width:{100 * lw / w:.3f}%;height:{100 * lh / h:.3f}%"
    )
    blend = " blend-normal" if layer.get("blend") == "normal" else ""
    return void(
        "img",
        class_=f"layer{blend}",
        src=str(layer["file"]),
        alt="",
        aria_hidden="true",
        data_motion=str(layer.get("motion", "none")),
        data_travel=f"{float(layer.get('travel', 0)) / h * 100:.3f}",
        style=style,
    )


def _spots(
    b: Builder, spots: list[Mapping[str, Any]], anchors: Mapping[str, Any], w: int, h: int
) -> tuple[str, str]:
    if not spots:
        return "", ""
    buttons = ""
    cards = ""
    for k, spot in enumerate(spots):
        point = anchors.get(str(spot.get("anchor", "")))
        if not point:
            continue
        left = 100 * float(point[0]) / w
        top = 100 * float(point[1]) / h
        side = "side-l" if left < 50 else "side-r"
        dot = tag("span", str(k + 1), class_="spot-dot", aria_hidden="true")
        label = (
            tag("span", b.inline(spot["label"]), class_="spot-label") if spot.get("label") else ""
        )
        buttons += tag(
            "button",
            dot + label,
            type="button",
            class_=f"spot {side}",
            data_spot=k,
            aria_label=None
            if spot.get("label")
            else str(b.plain_text(str(spot.get("title", k + 1)))),
            style=f"left:{left:.2f}%;top:{top:.2f}%",
        )
        title = tag("h4", b.inline(spot.get("title", spot.get("label", ""))))
        cards += tag(
            "div",
            title + b.paras(spot.get("text", "")),
            class_="spot-card",
            data_spot=k,
            hidden=True,
        )
    return buttons, tag("div", cards, class_="spot-cards", aria_live="polite")
