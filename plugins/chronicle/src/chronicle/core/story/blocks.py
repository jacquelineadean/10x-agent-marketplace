"""HTML for each block type. The runtime script enhances the figures; the words stand alone."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from chronicle.core.story.facts import format_value
from chronicle.core.story.html import tag, void
from chronicle.core.story.markup import plain

if TYPE_CHECKING:
    from chronicle.core.story.render import Builder

Block = Mapping[str, Any]


ROLES = ("accent", "legacy", "muted", "good", "bad", "warn", "ink")


def css_color(name: Any, index: int) -> str:
    """A story color name as CSS: a role, s1 to s6 or a theme color; else a series color.

    The default skips s1 and s2, which belong to the new and the old system, so group
    colors (squads, teams) never read as status.
    """
    value = str(name or "")
    if value in ROLES:
        return f"var(--{value})"
    if len(value) == 2 and value[0] == "s" and value[1] in "123456":
        return f"var(--{value})"
    if value.replace("-", "").isalnum() and value[:1].isalpha():
        return f"var(--c-{value.removeprefix('c-')})"
    return f"var(--s{(index + 2) % 6 + 1})"


def mount(b: Builder, label: Any = "") -> str:
    text = str(b.plain_text(str(label))) if label else ""
    return tag("div", class_="mount", role="img", aria_label=text or None)


def prose(b: Builder, block: Block) -> str:
    body = b.paras(block["text"], "lead" if block.get("lead") else "")
    cls = "prose col dropcap" if block.get("dropcap") else "prose col"
    return tag("div", body, class_=cls)


def stats(b: Builder, block: Block) -> str:
    """Big numbers: ruled columns, cards, or a printed receipt or ticket stub."""
    style = str(block.get("style") or b.theme.stats)
    items = ""
    sparks: dict[str, Any] = {}
    for k, item in enumerate(block["items"]):
        trend = str(item.get("trend", "neutral"))
        delta = (
            tag("p", b.inline(item["delta"]), class_=f"stat-delta {trend}")
            if item.get("delta")
            else ""
        )
        spark = ""
        if item.get("spark"):
            sparks[str(k)] = item["spark"]
            spark = tag("svg", class_="spark", aria_hidden="true")
        items += tag(
            "div",
            tag("p", b.inline(item.get("label", "")), class_="stat-label")
            + tag("p", b.inline(item["value"]), class_="stat-value")
            + delta
            + spark,
            class_="stat",
            data_i=k,
        )
    fid = b.register({"type": "stats", "sparks": sparks})
    title = tag("h3", b.inline(block["title"]), class_="stats-title") if block.get("title") else ""
    sub = tag("p", b.inline(block["subtitle"]), class_="stats-sub") if block.get("subtitle") else ""
    if style in ("receipt", "ticket"):
        paper = tag(
            "div",
            title + sub + tag("div", items, class_="stats") + tag("p", class_="rc-code"),
            class_="rc-paper",
        )
        return tag("div", paper, class_=f"stats-wrap stats-{style}", data_fig=fid)
    return tag(
        "div",
        title + sub + tag("div", items, class_="stats"),
        class_=f"stats-wrap wide stats-{style}",
        data_fig=fid,
    )


def lesson(b: Builder, block: Block) -> str:
    art = ""
    entry = b.manifest.get(str(block.get("art"))) if block.get("art") else None
    if entry:
        b.art_files.append(str(entry["file"]))
        art = void("img", class_="lesson-art", src=str(entry["file"]), alt="", aria_hidden="true")
    kicker = tag("p", b.inline(block.get("title", "The lesson")), class_="lesson-kicker")
    return tag("aside", art + kicker + b.paras(block["text"]), class_="lesson col")


def quote(b: Builder, block: Block) -> str:
    who = ""
    if block.get("who"):
        role = (
            ", " + tag("span", b.inline(block["role"]), class_="role") if block.get("role") else ""
        )
        who = tag("figcaption", b.inline(block["who"]) + role)
    return tag("figure", tag("blockquote", b.inline(block["text"])) + who, class_="pull col")


def chart(b: Builder, block: Block) -> str:
    fid = b.register(block)
    width = " wide" if block.get("wide", True) else " col"
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    return tag(
        "figure",
        b.heading(block)
        + mount(b, block.get("title", "Chart"))
        + tag("div", class_="table-slot", hidden=True)
        + note
        + b.source_line(block),
        class_=f"fig chart{width}",
        data_fig=fid,
    )


def scrolly(b: Builder, block: Block) -> str:
    fid = b.register(block)
    steps = "".join(
        tag(
            "div",
            tag("div", b.paras(step.get("text", "")), class_="step-card"),
            class_="step",
            data_step=k,
        )
        for k, step in enumerate(block["steps"])
    )
    spec = block["chart"]
    figure = tag(
        "figure",
        b.heading(spec)
        + mount(b, spec.get("title", "Chart"))
        + tag("div", class_="table-slot", hidden=True)
        + b.source_line(block),
        class_="fig chart",
    )
    return tag(
        "section",
        tag("div", figure, class_="scrolly-graphic") + tag("div", steps, class_="scrolly-steps"),
        class_="scrolly wide",
        data_fig=fid,
    )


def timeline(b: Builder, block: Block) -> str:
    fid = b.register(block)
    events = ""
    for k, ev in enumerate(block["events"]):
        raw = str(ev.get("date", ""))
        when = format_value(raw, fmt="date" if len(raw) > 7 else "month")
        events += tag(
            "li",
            tag("time", plain(when), datetime=raw)
            + tag("p", b.inline(ev.get("title", "")), class_="ev-title")
            + b.paras(ev.get("text", ""), "ev-text"),
            class_=f"ev {ev.get('kind', 'milestone')}",
            data_i=k,
        )
    return tag(
        "figure",
        b.heading(block)
        + tag("div", class_="mount", aria_hidden="true")
        + tag("ol", events, class_="tl-list")
        + b.source_line(block, table=False),
        class_="fig timeline wide",
        data_fig=fid,
    )


def stepper(b: Builder, block: Block) -> str:
    fid = b.register(block)
    steps = ""
    for k, step in enumerate(block["steps"]):
        time = tag("p", b.inline(step["time"]), class_="st-time") if step.get("time") else ""
        steps += tag(
            "li",
            time
            + tag("p", b.inline(step.get("title", "")), class_="st-title")
            + b.paras(step.get("text", "")),
            class_="st",
            data_i=k,
        )
    controls = tag(
        "div",
        tag("button", "Back", type="button", class_="st-prev")
        + tag("p", class_="st-count", aria_live="polite")
        + tag("button", "Next", type="button", class_="st-next"),
        class_="st-controls",
        hidden=True,
    )
    panel = tag("div", tag("ol", steps, class_="st-list") + controls, class_="st-panel")
    chart_mount = mount(b, block.get("title", "Chart")) if block.get("chart") else ""
    return tag(
        "figure",
        b.heading(block) + chart_mount + panel + b.source_line(block, table=False),
        class_="fig stepper wide",
        data_fig=fid,
    )


def compare(b: Builder, block: Block) -> str:
    labels = block.get("labels", ["Before", "After"])

    def face(side: str, label: str, item: Block, value: str, note: str) -> str:
        extra = tag("span", b.inline(note), class_="face-note") if note else ""
        return tag(
            "span",
            tag("span", b.inline(label), class_="face-tag")
            + tag("span", b.inline(item.get("label", "")), class_="face-label")
            + tag("span", b.inline(value), class_="face-value")
            + extra,
            class_=f"face {side}",
        )

    cards = "".join(
        tag(
            "li",
            tag(
                "button",
                face("front", labels[0], item, str(item.get("before", "")), "")
                + face(
                    "back", labels[1], item, str(item.get("after", "")), str(item.get("note", ""))
                ),
                type="button",
                class_="flip",
                aria_pressed="false",
            ),
            class_="card",
        )
        for item in block["items"]
    )
    fid = b.register({"type": "compare", "labels": labels})
    toggle = tag(
        "div",
        tag("button", b.inline(labels[0]), type="button", data_side="0", aria_pressed="true")
        + tag("button", b.inline(labels[1]), type="button", data_side="1", aria_pressed="false"),
        class_="seg",
        role="group",
        aria_label="Show",
    )
    return tag(
        "figure",
        b.heading(block) + toggle + tag("ul", cards, class_="cards"),
        class_="fig compare wide",
        data_fig=fid,
    )


def matrix(b: Builder, block: Block) -> str:
    fid = b.register(block)
    rows = ""
    for k, item in enumerate(block["items"]):
        button = tag(
            "button",
            tag("span", plain(str(item.get("id", k + 1))), class_="risk-id")
            + tag("span", b.inline(item.get("title", "")), class_="risk-title"),
            type="button",
            class_="risk-btn",
            aria_expanded="false",
        )
        body = b.paras(item.get("text", "")) + tag(
            "p", b.inline(item.get("owner", "")), class_="risk-meta"
        )
        rows += tag("li", button + tag("div", body, class_="risk-body"), class_="risk", data_i=k)
    grid = tag(
        "div", mount(b, "Risk matrix") + tag("ol", rows, class_="risk-list"), class_="matrix-grid"
    )
    return tag(
        "figure",
        b.heading(block) + grid + b.source_line(block, table=False),
        class_="fig matrix wide",
        data_fig=fid,
    )


def roadmap(b: Builder, block: Block) -> str:
    fid = b.register(block)
    items = ""
    for k, item in enumerate(block["items"]):
        items += tag(
            "li",
            tag("p", b.inline(item.get("when", "")), class_="rm-when")
            + tag("p", b.inline(item.get("title", "")), class_="rm-title")
            + b.paras(item.get("text", ""), "rm-text"),
            class_=f"rm {item.get('confidence', 'committed')}",
            data_i=k,
        )
    return tag(
        "figure",
        b.heading(block)
        + mount(b, "Roadmap")
        + tag("ol", items, class_="rm-list")
        + b.source_line(block, table=False),
        class_="fig roadmap wide",
        data_fig=fid,
    )


def team(b: Builder, block: Block) -> str:
    fid = b.register(block)
    cards = ""
    for k, squad in enumerate(block["squads"]):
        members = "".join(
            tag("li", plain("".join(word[0] for word in str(m).split()[:2])), title=str(m))
            for m in squad.get("members", [])
        )
        owns = "".join(tag("li", plain(str(s))) for s in squad.get("owns", []))
        cards += tag(
            "li",
            tag("p", b.inline(squad.get("name", "")), class_="squad-name")
            + tag("p", b.inline(squad.get("lead", "")), class_="squad-lead")
            + b.paras(squad.get("focus", ""), "squad-focus")
            + tag("ul", members, class_="members", aria_label="Members")
            + tag("ul", owns, class_="owns", aria_label="Owns"),
            class_="squad",
            data_i=k,
            style=f"--squad:{css_color(squad.get('color'), k)}",
        )
    return tag(
        "figure",
        b.heading(block) + tag("ul", cards, class_="squads") + b.source_line(block, table=False),
        class_="fig team wide",
        data_fig=fid,
    )


def model(b: Builder, block: Block) -> str:
    fid = b.register(block)
    grid = tag(
        "div",
        tag("div", class_="controls") + mount(b, block.get("title", "")),
        class_="model-grid",
    )
    return tag(
        "figure",
        b.heading(block)
        + grid
        + tag("p", class_="readout", aria_live="polite")
        + b.paras(block.get("text", ""), "fig-note")
        + b.source_line(block, table=False),
        class_="fig model wide",
        data_fig=fid,
    )


def table(b: Builder, block: Block) -> str:
    head = "".join(tag("th", b.inline(c), scope="col") for c in block["columns"])
    rows = "".join(
        tag("tr", "".join(tag("td", b.inline(cell)) for cell in row)) for row in block["rows"]
    )
    note = tag("p", b.inline(block["caption"]), class_="fig-note") if block.get("caption") else ""
    grid = tag("table", tag("thead", tag("tr", head)) + tag("tbody", rows))
    return tag(
        "figure",
        b.heading(block)
        + tag("div", grid, class_="table-scroll")
        + note
        + b.source_line(block, table=False),
        class_="fig table-fig wide",
    )


def plate(b: Builder, block: Block) -> str:
    return b.plate(
        str(block["art"]),
        block.get("caption", ""),
        str(block.get("width", "wide")),
        block.get("spots"),
    )


RENDERERS: dict[str, Callable[[Builder, Block], str]] = {
    "prose": prose,
    "stats": stats,
    "lesson": lesson,
    "quote": quote,
    "chart": chart,
    "scrolly": scrolly,
    "timeline": timeline,
    "stepper": stepper,
    "compare": compare,
    "matrix": matrix,
    "roadmap": roadmap,
    "team": team,
    "model": model,
    "table": table,
    "plate": plate,
}
