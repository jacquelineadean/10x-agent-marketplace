"""The `sequence` kind: who calls whom, in order, as lifelines and messages.

Claude writes participants and messages; code places the lifelines, draws each message as
an arrow with its label, and plays them in order. A message is `sync` (solid, filled
head), `async` (solid, open head) or `reply` (dashed, open head).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from chronicle_engine.core.story.model import Report

from blueprint.core import drawn

WIDTH = 960
TOP = 12
BOX_H = 44
ROW = 46
KINDS = ("sync", "async", "reply")
SKELETON = {
    "participants": [{"id": "client", "label": "Client"}, {"id": "api", "label": "API"}],
    "messages": [{"from": "client", "to": "api", "label": "request"}],
}


def validate(spec: Mapping[str, Any], report: Report) -> None:
    people = spec.get("participants")
    if not isinstance(people, list) or len(people) < 2:
        report.errors.append("sequence.participants needs at least two {id, label}")
        return
    ids = [str(p.get("id", "")) for p in people if isinstance(p, Mapping)]
    if len(set(ids)) != len(ids) or "" in ids:
        report.errors.append("sequence.participants each need a unique id")
    messages = spec.get("messages")
    if not isinstance(messages, list) or not messages:
        report.errors.append("sequence.messages needs at least one {from, to, label}")
        return
    for k, m in enumerate(messages):
        if not isinstance(m, Mapping):
            report.errors.append(f"sequence.messages[{k}] must be an object")
            continue
        for end in ("from", "to"):
            if m.get(end) not in ids:
                report.errors.append(f"sequence.messages[{k}].{end} names no participant")
        if m.get("kind", "sync") not in KINDS:
            report.errors.append(f"sequence.messages[{k}].kind must be one of {', '.join(KINDS)}")


def message_id(k: int, m: Mapping[str, Any]) -> str:
    return str(m.get("id") or f"m{k + 1}")


def _label_box(m: Mapping[str, Any], a: float, b: float) -> tuple[float, float, float]:
    """Where a message's label sits: its baseline x, the anchor, and its left and right x."""
    width = len(str(m.get("label", ""))) * 6.6 + 8
    if a == b:
        return a + 54, a + 50, a + 50 + width
    middle = (a + b) / 2
    return middle, middle - width / 2, middle + width / 2


def _lifeline(cx: float, top: float, bottom: float, holes: Sequence[tuple[float, float]]) -> str:
    """A dashed lifeline with a gap wherever a label crosses it."""
    segments = ""
    y = top
    for start, stop in sorted(holes):
        if start > y:
            segments += f"M{cx:g} {y:g} L{cx:g} {start:g} "
        y = max(y, stop)
    if bottom > y:
        segments += f"M{cx:g} {y:g} L{cx:g} {bottom:g}"
    return f'<path class="line dashed" d="{segments.strip()}"/>'


def draw(spec: Mapping[str, Any]) -> str:
    people = list(spec["participants"])
    messages = list(spec["messages"])
    col = (WIDTH - 40) / len(people)
    x = {str(p["id"]): 20 + col * (i + 0.5) for i, p in enumerate(people)}
    height = TOP + BOX_H + 30 + ROW * len(messages) + 10
    w = min(170.0, col - 14)
    rows = []
    for k, m in enumerate(messages):
        y = TOP + BOX_H + 34 + ROW * k
        a, b = x[str(m["from"])], x[str(m["to"])]
        rows.append((k, m, y, a, b, *_label_box(m, a, b)))
    parts = ""
    for p in people:
        cx = x[str(p["id"])]
        holes = [(y - 20, y - 2) for _, _, y, _, _, _, left, right in rows if left < cx < right]
        parts += (
            f'<g id="p-{p["id"]}">'
            f'<rect class="box" x="{cx - w / 2:g}" y="{TOP}" width="{w:g}" '
            f'height="{BOX_H}" rx="6"/>'
            + drawn.text("title", cx, TOP + 27, p.get("label", p["id"]), "middle")
            + _lifeline(cx, TOP + BOX_H, height - 6, holes)
            + "</g>"
        )
    for k, m, y, a, b, label_x, _, _ in rows:
        mid = message_id(k, m)
        style = m.get("kind", "sync")
        line = "line dashed" if style == "reply" else "line"
        if a == b:
            right, top, low = a + 46, y - 10, y + 8
            path = f"M{a:g} {top:g} L{right:g} {top:g} L{right:g} {low:g} L{a + 4:g} {low:g}"
            tip = drawn.head(a + 4, y + 8, -1, style == "sync")
            anchor = "start"
        else:
            direction = 1 if b > a else -1
            path = f"M{a:g} {y:g} L{b - 2 * direction:g} {y:g}"
            tip = drawn.head(b - 2 * direction, y, direction, style == "sync")
            anchor = "middle"
        parts += (
            f'<g id="{mid}">'
            f'<path id="{mid}-path" class="{line}" d="{path}"/>{tip}'
            + drawn.text("label", label_x, y - 7, m.get("label", ""), anchor)
            + "</g>"
        )
    return drawn.svg(WIDTH, height, parts)


def default_steps(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    """One step per message, captioned with its label; every participant shows first."""
    people = [f"p-{p['id']}" for p in spec["participants"]]
    steps = []
    for k, m in enumerate(spec["messages"]):
        mid = message_id(k, m)
        step: dict[str, Any] = {
            "caption": str(m.get("label", "")),
            "draw": [mid],
            "flow": [f"{mid}-path"],
        }
        if k == 0:
            step["show"] = people
        steps.append(step)
    return steps


SEQUENCE = drawn.kind(
    "sequence",
    draw,
    validate,
    default_steps,
    SKELETON,
    "write the participants and messages; steps are optional",
)
