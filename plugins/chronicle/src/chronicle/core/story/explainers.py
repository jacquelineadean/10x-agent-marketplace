"""HTML for explanatory figures: tile maps, flows, diagrams and custom widgets."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from chronicle.core.story import geo
from chronicle.core.story.blocks import mount
from chronicle.core.story.diagram import sanitize
from chronicle.core.story.html import tag
from chronicle.core.story.markup import plain

if TYPE_CHECKING:
    from chronicle.core.story.render import Builder

Block = Mapping[str, Any]


def tilemap(b: Builder, block: Block) -> str:
    """A tile map; with frames, a slider and a play button walk it through time."""
    spec = dict(block)
    spec["tiles"] = (
        list(block["tiles"])
        if block.get("layout") == "custom"
        else geo.tiles(str(block.get("layout", "us-states")))
    )
    fid = b.register(spec)
    controls = ""
    if block.get("frames"):
        controls = tag(
            "div",
            tag("p", class_="tm-frame", aria_hidden="true")
            + tag("button", "Play", type="button", class_="tm-play btn")
            + tag("input", type="range", class_="tm-range", aria_label="Point in time", min="0"),
            class_="tm-ctrl",
            hidden=True,
        )
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + controls
        + tag("p", class_="tm-readout", aria_live="polite")
        + mount(b, block.get("title", "Map"))
        + tag("div", class_="tm-legend")
        + tag("div", class_="table-slot", hidden=True)
        + note
        + b.source_line(block),
        class_="fig tilemap wide",
        data_fig=fid,
    )


def flow(b: Builder, block: Block) -> str:
    """A process as a row of steps; a toggle compares two states of every step."""
    labels = [str(x) for x in block.get("labels", [])]
    fid = b.register(block)
    nodes = ""
    for k, node in enumerate(block["nodes"]):
        values = node.get("values", [])
        values = values if isinstance(values, list) else [values]
        status = node.get("status", [])
        status = status if isinstance(status, list) else [status]
        first = status[-1] if status else ""
        value = tag("span", b.inline(values[-1]), class_="fl-val") if values else ""
        nodes += tag(
            "li",
            tag(
                "button",
                tag("span", str(k + 1), class_="fl-step", aria_hidden="true")
                + tag("span", b.inline(node.get("label", "")), class_="fl-label")
                + (tag("span", b.inline(node["sub"]), class_="fl-sub") if node.get("sub") else "")
                + value,
                type="button",
                class_="fl-btn",
                aria_pressed="false",
            )
            + tag("div", b.paras(node.get("text", "")), class_="fl-text"),
            class_=f"fl-node st-{plain(str(first))}",
            data_i=k,
        )
    toggle = ""
    if len(labels) > 1:
        toggle = tag(
            "div",
            "".join(
                tag(
                    "button",
                    b.inline(label),
                    type="button",
                    data_side=str(i),
                    aria_pressed="true" if i == len(labels) - 1 else "false",
                )
                for i, label in enumerate(labels)
            ),
            class_="seg",
            role="group",
            aria_label="Show",
            hidden=True,
        )
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + toggle
        + tag("div", tag("ol", nodes, class_="fl-nodes"), class_="fl-track")
        + tag("div", class_="fl-detail", aria_live="polite")
        + tag("div", class_="fl-legend")
        + note
        + b.source_line(block, table=False),
        class_="fig flow wide",
        data_fig=fid,
    )


def diagram(b: Builder, block: Block) -> str:
    """Claude's SVG, sanitized, with optional steps that focus parts of it."""
    source = str(block["svg"])
    text = source if source.lstrip().startswith("<svg") else b.files.get(source, "")
    if not text:
        raise ValueError(f"diagram file {source!r} was not read")
    b.counter += 1
    prefix = f"dg{b.counter}"

    def fill(raw: str) -> str:
        return str(b.plain_text(raw))

    drawing = sanitize(text, prefix, fill)
    steps = list(block.get("steps", []))
    spec = {
        "type": "diagram",
        "prefix": prefix,
        "steps": [{"focus": [f"{prefix}-{f}" for f in step.get("focus", [])]} for step in steps],
    }
    fid = b.register(spec)
    panel = ""
    if steps:
        items = "".join(
            tag(
                "li",
                tag("p", b.inline(step.get("title", "")), class_="st-title")
                + b.paras(step.get("text", "")),
                class_="st",
                data_i=k,
            )
            for k, step in enumerate(steps)
        )
        controls = tag(
            "div",
            tag("button", "Back", type="button", class_="st-prev")
            + tag("p", class_="st-count", aria_live="polite")
            + tag("button", "Next", type="button", class_="st-next"),
            class_="st-controls",
            hidden=True,
        )
        panel = tag("div", tag("ol", items, class_="st-list") + controls, class_="st-panel")
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    alt = str(b.plain_text(str(block.get("alt", block.get("title", "Diagram")))))
    width = "col" if block.get("width") == "column" else "wide"
    return tag(
        "figure",
        b.heading(block)
        + tag("div", drawing.markup, class_="dg-wrap", role="img", aria_label=alt)
        + tag("p", "Scroll sideways to see the whole diagram.", class_="dg-hint")
        + panel
        + note
        + b.source_line(block, table=False),
        class_=f"fig diagram stepper {width}",
        data_fig=fid,
    )


def widget(b: Builder, block: Block) -> str:
    """A custom interactive written for this page; its script registers under `name`."""
    name = str(block["name"])
    b.widgets[name] = str(block["script"])
    fid = b.register(
        {
            "type": "widget",
            "name": name,
            "data": block.get("data", {}),
            "height": block.get("height"),
        }
    )
    fallback = (
        tag("div", b.paras(block["fallback"]), class_="widget-fallback")
        if block.get("fallback")
        else ""
    )
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + tag("div", class_="widget-root", data_widget=name)
        + fallback
        + note
        + b.source_line(block, table=False),
        class_=f"fig widget wide w-{name}",
        data_fig=fid,
    )


RENDERERS: dict[str, Callable[[Builder, Block], str]] = {
    "tilemap": tilemap,
    "flow": flow,
    "diagram": diagram,
    "widget": widget,
}
