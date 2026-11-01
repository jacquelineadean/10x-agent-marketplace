"""Plates: the painter's images on a story page, with moving layers, labels and hotspots.

chronicle's art provider draws these for `hero.art`, `chapters[].art` and the `plate` block.
A plate block may also carry notes: red-pen marks drawn over the painting that write
themselves once it has developed.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag, void
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

MARKS = ("circle", "underline", "arrow", "cross", "tick", "box")
PENS = {"red": "#B8322A", "blue": "#2E58A6", "ink": "#2B231D"}


def plate(
    b: Builder,
    key: str,
    caption: Any = "",
    width: str = "wide",
    spots: Any = None,
    notes: Any = None,
    extra: str = "",
) -> str:
    """A painting: base image, moving layers, an overlay for lines, optional hotspots.

    `extra` is markup placed on the stage over the painting, such as a room's doorways.
    """
    entry = b.manifest.get(key)
    if not entry:
        return ""
    scene = b.story.get("art", {}).get(key, {})
    w, h = int(entry["width"]), int(entry["height"])
    b.art_files.append(str(entry["file"]))
    layers = _layers(b, entry, w, h)
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
        "".join(_label(b, lab) for lab in entry.get("labels", []))
        + _notes(b, notes or [], anchors, w),
        class_="overlay",
        viewBox=f"0 0 {w} {h}",
        preserveAspectRatio="none",
        aria_hidden="true",
    )
    stage = tag(
        "div",
        base + layers + overlay + spot_html + extra,
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


def _layers(b: Builder, entry: Mapping[str, Any], w: int, h: int) -> str:
    """Moving layers in paint order; a rig's parts gather into one figure where it first paints."""
    out = ""
    done: set[str] = set()
    found = entry.get("layers", [])
    for layer in found:
        rig = str(layer.get("rig", ""))
        if not rig:
            out += _layer(b, layer, w, h)
        elif rig not in done:
            done.add(rig)
            parts = [x for x in found if x.get("rig") == rig]
            out += rig_html(b, rig, entry.get("rigs", {}).get(rig, {}), parts, w, h)
    return out


def rig_box(parts: list[Mapping[str, Any]]) -> tuple[float, float, float, float]:
    """The box that spans a rig's parts: x, y, width and height in painting pixels."""
    x0 = min(float(p["box"][0]) for p in parts)
    y0 = min(float(p["box"][1]) for p in parts)
    x1 = max(float(p["box"][0]) + float(p["box"][2]) for p in parts)
    y1 = max(float(p["box"][1]) + float(p["box"][3]) for p in parts)
    return x0, y0, max(1.0, x1 - x0), max(1.0, y1 - y0)


def rig_parts(b: Builder, parts: list[Mapping[str, Any]]) -> str:
    """A rig's parts in paint order, placed in percent of the rig box, each about its pivot."""
    x0, y0, rw, rh = rig_box(parts)
    imgs = ""
    for p in parts:
        b.art_files.append(str(p["file"]))
        px, py, pw, ph = (float(v) for v in p["box"])
        pivot = p.get("pivot") or [px + pw / 2, py + ph / 2]
        values = dict(p.get("part", {}))
        imgs += void(
            "img",
            class_="part",
            src=str(p["file"]),
            alt="",
            aria_hidden="true",
            data_role=str(values.get("role", "static")),
            **{
                f"data_{k}": f"{float(v):g}" for k, v in values.items() if k not in ("role", "name")
            },
            style=(
                f"left:{100 * (px - x0) / rw:.3f}%;top:{100 * (py - y0) / rh:.3f}%;"
                f"width:{100 * pw / rw:.3f}%;height:{100 * ph / rh:.3f}%;"
                f"transform-origin:{100 * (float(pivot[0]) - px) / pw:.1f}% "
                f"{100 * (float(pivot[1]) - py) / ph:.1f}%"
            ),
        )
    return imgs


def rig_html(
    b: Builder, name: str, rig: Mapping[str, Any], parts: list[Mapping[str, Any]], w: int, h: int
) -> str:
    """One rig on a plate: its parts inside a box that spans them all, playing its gait."""
    x0, y0, rw, rh = rig_box(parts)
    foot = rig.get("foot") or [x0 + rw / 2, y0 + rh]
    roam = rig.get("roam")
    return tag(
        "span",
        rig_parts(b, parts),
        class_="rig",
        data_fig=b.register({"type": "rig", "name": name}),
        data_rig=name,
        data_gait=str(rig.get("gait", "still")),
        data_bob=f"{float(rig.get('bob', 2)):g}",
        data_h=f"{rh:g}",
        data_w=f"{rw:g}",
        data_foot=f"{100 * (float(foot[0]) - x0) / rw:.1f}",
        data_speed=f"{float(rig.get('speed', 30)):g}",
        data_stride=f"{float(rig.get('stride', 60)):g}",
        data_roam=f"{100 * float(roam[0]) / w:.2f} {100 * float(roam[1]) / w:.2f}"
        if roam
        else None,
        style=(
            f"left:{100 * x0 / w:.3f}%;top:{100 * y0 / h:.3f}%;"
            f"width:{100 * rw / w:.3f}%;height:{100 * rh / h:.3f}%"
        ),
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


# ------------------------------------------------------------------- notes
def point(at: Any, anchors: Mapping[str, Any]) -> tuple[float, float] | None:
    """An anchor's point, or an [x, y] pair in painting pixels."""
    if isinstance(at, str):
        found = anchors.get(at)
        return (float(found[0]), float(found[1])) if found else None
    if isinstance(at, list | tuple) and len(at) == 2:
        return (float(at[0]), float(at[1]))
    return None


def check_at(at: Any, where: str, known: set[str], report: Any) -> None:
    """An `at` must name an anchor the drawing has, or be [x, y] in painting pixels."""
    if isinstance(at, str):
        if known and at not in known:
            report.errors.append(f"{where} {at!r} is no data-anchor in the drawing")
    elif not (
        isinstance(at, list) and len(at) == 2 and all(isinstance(v, int | float) for v in at)
    ):
        report.errors.append(f"{where} must name an anchor or be [x, y] in painting pixels")


def _wobble(rng: random.Random, size: float) -> float:
    return rng.uniform(-1.0, 1.0) * size


def _loop(rng: random.Random, x: float, y: float, r: float) -> str:
    """A pen circle: a little over one turn, wider than tall, never quite closing."""
    start = rng.uniform(0, 2 * math.pi)
    points = []
    for i in range(27):
        a = start + 2.15 * math.pi * i / 26
        rr = r * (1 + 0.07 * math.sin(3 * a + start)) + _wobble(rng, r * 0.03)
        points.append((x + 1.3 * rr * math.cos(a), y + rr * math.sin(a)))
    d = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    for (ax, ay), (bx, by) in zip(points[1:-1], points[2:], strict=True):
        d += f" Q{ax:.1f} {ay:.1f} {(ax + bx) / 2:.1f} {(ay + by) / 2:.1f}"
    return d


def _stroke(rng: random.Random, a: tuple[float, float], b: tuple[float, float]) -> str:
    """One hand-drawn line: a slight bow, so it never looks ruled."""
    mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    length = math.hypot(b[0] - a[0], b[1] - a[1]) or 1.0
    nx, ny = -(b[1] - a[1]) / length, (b[0] - a[0]) / length
    bow = _wobble(rng, length * 0.06)
    return f"M{a[0]:.1f} {a[1]:.1f} Q{mx + nx * bow:.1f} {my + ny * bow:.1f} {b[0]:.1f} {b[1]:.1f}"


def mark_path(mark: str, x: float, y: float, size: float, seed: int, tail: Any = None) -> str:
    """Path data for one pen mark around (x, y); `tail` is where an arrow starts."""
    rng = random.Random(f"pen-{seed}")  # noqa: S311  seeded jitter for a hand-drawn look, not security
    s = size
    if mark == "underline":
        return _stroke(rng, (x - s, y + s * 0.45), (x + s, y + s * 0.38))
    if mark == "cross":
        return (
            _stroke(rng, (x - s * 0.5, y - s * 0.5), (x + s * 0.5, y + s * 0.5))
            + " "
            + (_stroke(rng, (x + s * 0.5, y - s * 0.5), (x - s * 0.5, y + s * 0.5)))
        )
    if mark == "tick":
        return (
            f"M{x - s * 0.5:.1f} {y:.1f} L{x - s * 0.12:.1f} {y + s * 0.42:.1f} "
            f"L{x + s * 0.62:.1f} {y - s * 0.55:.1f}"
        )
    if mark == "box":
        corners = [
            (x - s, y - s * 0.7),
            (x + s, y - s * 0.7),
            (x + s, y + s * 0.7),
            (x - s, y + s * 0.7),
        ]
        return " ".join(_stroke(rng, corners[i], corners[(i + 1) % 4]) for i in range(4))
    if mark == "arrow":
        tx, ty = tail if tail else (x + s * 2, y - s * 1.5)
        angle = math.atan2(y - ty, x - tx)
        tip = (x - math.cos(angle) * s * 0.35, y - math.sin(angle) * s * 0.35)
        head = ""
        for turn in (2.6, -2.6):
            hx = tip[0] + math.cos(angle + turn) * s * 0.42
            hy = tip[1] + math.sin(angle + turn) * s * 0.42
            head += f" M{tip[0]:.1f} {tip[1]:.1f} L{hx:.1f} {hy:.1f}"
        return _stroke(rng, (tx, ty), tip) + head
    return _loop(rng, x, y, s)


def _notes(b: Builder, notes: list[Mapping[str, Any]], anchors: Mapping[str, Any], w: int) -> str:
    """Red-pen marks and words over the painting, each drawn a beat after the last."""
    out = ""
    for k, note in enumerate(notes):
        found = point(note.get("at"), anchors)
        if found is None:
            continue
        x, y = found
        size = float(note.get("size", w * 0.045))
        mark = str(note.get("mark", "circle"))
        color = PENS.get(str(note.get("pen", "red")), PENS["red"])
        words = str(b.plain_text(str(note.get("text", "")))) if note.get("text") else ""
        dx = float(note.get("dx", size * 1.6))
        dy = float(note.get("dy", -size * 1.2))
        text_at = (x + dx, y + dy)
        stroke = f"{max(2.0, w / 420):.1f}"
        delay = f"--d:{0.45 * k:.2f}s"
        path = tag(
            "path",
            class_="pen",
            d=mark_path(mark, x, y, size, k + 1, text_at if mark == "arrow" else None),
            pathLength="1",
            stroke=color,
            stroke_width=stroke,
            style=delay,
        )
        text = (
            tag(
                "text",
                plain(words),
                class_="pen-text",
                x=f"{text_at[0]:.1f}",
                y=f"{text_at[1]:.1f}",
                fill=color,
                font_size=f"{float(note.get('font', w / 46)):.1f}",
                text_anchor="start" if dx >= 0 else "end",
                style=delay,
            )
            if words
            else ""
        )
        out += tag("g", path + text, class_="note")
    # The notes are a figure of their own, so only pages with notes ship the pen parts.
    return tag("g", out, class_="notes", data_fig=b.register({"type": "notes"})) if out else ""
