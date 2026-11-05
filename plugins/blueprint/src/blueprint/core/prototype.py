"""The prototype layout: clickable screens of an app, fed by facts.

Each chapter is a screen behind a tab. Screens hold cards, lists, tables, charts and
widgets; a card or list row with `link` opens another screen, so a reviewer can click
through the flow. A toggle shows the screens at desktop or phone width.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.dispatch import render_block
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

SKELETON: list[dict[str, Any]] = [
    {
        "id": "home",
        "title": "Home",
        "blocks": [
            {
                "type": "cards",
                "items": [{"title": "A screen", "text": "Open it", "link": "detail"}],
            }
        ],
    },
    {
        "id": "detail",
        "title": "Detail",
        "blocks": [{"type": "list", "items": [{"title": "A row", "text": "Its details"}]}],
    },
]
STATUS = ("good", "warn", "bad", "none")
CARDS = (("items",), ("title", "subtitle", "source"))
LIST = (("items",), ("title", "subtitle", "source"))
FULL = ("cards", "list", "table", "stats", "timeline", "roadmap")


def _status(item: Mapping[str, Any]) -> str:
    status = str(item.get("status", "none"))
    return status if status in STATUS else "none"


def cards(b: Builder, block: Mapping[str, Any]) -> str:
    """A grid of cards; a card with `link` opens that screen."""
    fid = b.register({"type": "cards"})
    out = ""
    for item in block["items"]:
        body = (
            tag("p", b.inline(item.get("title", "")), class_="card-title")
            + (tag("p", b.inline(item["value"]), class_="card-value") if item.get("value") else "")
            + (tag("p", b.inline(item["text"]), class_="card-text") if item.get("text") else "")
        )
        cls = f"card status-{_status(item)}"
        if item.get("link"):
            out += tag(
                "button",
                body,
                type="button",
                class_=cls + " card-link",
                data_link=str(item["link"]),
            )
        else:
            out += tag("div", body, class_=cls)
    return tag(
        "div",
        b.heading(block) + tag("div", out, class_="card-grid"),
        class_="cards wide",
        data_fig=fid,
    )


def plist(b: Builder, block: Mapping[str, Any]) -> str:
    """Rows with a title, a status and more text; a row opens its text or another screen."""
    fid = b.register({"type": "list"})
    rows = ""
    for k, item in enumerate(block["items"]):
        chip = (
            tag("span", plain(str(item["status"])), class_="plist-chip")
            if item.get("status")
            else ""
        )
        head = (
            tag("span", b.inline(item.get("title", "")), class_="plist-title")
            + (tag("span", b.inline(item["meta"]), class_="plist-meta") if item.get("meta") else "")
            + chip
        )
        more = (
            tag("div", b.paras(item["text"]), class_="plist-more", id=f"{fid}-{k}", hidden=True)
            if item.get("text")
            else ""
        )
        attrs: dict[str, Any] = {"type": "button", "class_": "plist-row"}
        if item.get("link"):
            attrs["data_link"] = str(item["link"])
        elif more:
            attrs.update(aria_expanded="false", aria_controls=f"{fid}-{k}")
        rows += tag(
            "li", tag("button", head, **attrs) + more, class_=f"plist-item status-{_status(item)}"
        )
    return tag(
        "div",
        b.heading(block) + tag("ul", rows, class_="plist"),
        class_="plist-wrap wide",
        data_fig=fid,
    )


def _span(block: Mapping[str, Any]) -> int:
    return int(block.get("span", 2 if block.get("type") in FULL else 1))


def render(b: Builder, title: str) -> str:
    meta = b.story["meta"]
    screens = b.story["chapters"]
    tabs = "".join(
        tag(
            "button",
            b.inline(ch.get("short", ch["title"])),
            type="button",
            role="tab",
            class_="proto-tab",
            id=f"tab-{ch['id']}",
            aria_controls=str(ch["id"]),
            aria_selected="true" if i == 0 else "false",
        )
        for i, ch in enumerate(screens)
    )
    panels = ""
    for i, ch in enumerate(screens):
        cells = "".join(
            tag("div", render_block(b, block), class_=f"proto-cell span-{_span(block)}")
            for block in ch.get("blocks", [])
        )
        panels += tag(
            "section",
            tag("h2", b.inline(ch["title"]), class_="proto-h")
            + (tag("p", b.inline(ch["dek"]), class_="proto-dek") if ch.get("dek") else "")
            + tag("div", cells, class_="proto-grid"),
            class_="proto-screen",
            id=str(ch["id"]),
            role="tabpanel",
            aria_labelledby=f"tab-{ch['id']}",
            hidden=i != 0,
        )
    devices = tag(
        "div",
        tag(
            "button",
            "Desktop",
            type="button",
            class_="proto-device",
            data_device="desktop",
            aria_pressed="true",
        )
        + tag(
            "button",
            "Phone",
            type="button",
            class_="proto-device",
            data_device="phone",
            aria_pressed="false",
        ),
        class_="proto-devices",
        role="group",
        aria_label="Screen width",
    )
    top = tag(
        "header",
        tag("p", b.inline(meta.get("kicker", "")), class_="proto-kicker")
        + tag("h1", b.inline(meta["title"]), class_="proto-name")
        + devices
        + tag("button", type="button", class_="theme-btn", aria_label="Switch light or dark theme"),
        class_="proto-top",
    )
    frame = tag(
        "div",
        top + tag("nav", tabs, class_="proto-tabs", role="tablist", aria_label="Screens") + panels,
        class_="proto-frame",
        data_device="desktop",
    )
    dek = tag("p", b.inline(meta["dek"]), class_="proto-about") if meta.get("dek") else ""
    return tag(
        "main", dek + frame + b.sources_footer(), class_="prototype", id="top", aria_label=title
    )
