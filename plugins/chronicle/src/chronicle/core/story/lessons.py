"""HTML for teaching figures: quizzes and checklists, for onboarding pages and guides."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from chronicle.core.story.html import tag

if TYPE_CHECKING:
    from chronicle.core.story.render import Builder

Block = Mapping[str, Any]


def quiz(b: Builder, block: Block) -> str:
    """Questions answered one at a time; every answer explains itself."""
    questions = ""
    for k, q in enumerate(block["questions"]):
        options = "".join(
            tag(
                "li",
                tag(
                    "button",
                    tag("span", chr(ord("A") + i), class_="qz-key", aria_hidden="true")
                    + tag("span", b.inline(opt), class_="qz-opt-text"),
                    type="button",
                    class_="qz-opt",
                    data_k=i,
                ),
            )
            for i, opt in enumerate(q.get("options", []))
        )
        questions += tag(
            "li",
            tag("p", b.inline(q.get("q", "")), class_="qz-text")
            + tag("ol", options, class_="qz-opts")
            + tag("div", b.paras(q.get("explain", "")), class_="qz-explain"),
            class_="qz-q",
            data_i=k,
        )
    fid = b.register(
        {
            "type": "quiz",
            "answers": [int(q["answer"]) for q in block["questions"]],
            "results": [
                {
                    "min": float(r.get("min", 0)),
                    "label": str(b.plain_text(str(r.get("label", "")))),
                    "text": str(b.plain_text(str(r.get("text", "")))),
                }
                for r in block.get("results", [])
            ],
        }
    )
    kicker = tag("p", b.inline(block["kicker"]), class_="qz-kicker") if block.get("kicker") else ""
    return tag(
        "figure",
        kicker
        + b.heading(block)
        + tag("ol", questions, class_="qz-list")
        + tag("div", class_="qz-result", aria_live="polite", hidden=True),
        class_="fig quiz col",
        data_fig=fid,
    )


def checklist(b: Builder, block: Block) -> str:
    """Tasks a reader ticks off; ticks stay in this browser when it allows storage."""
    groups = ""
    count = 0
    for group in block["groups"]:
        items = ""
        for item in group.get("items", []):
            items += tag(
                "li",
                tag(
                    "label",
                    tag("input", type="checkbox", data_k=count) + tag("span", b.inline(item)),
                ),
            )
            count += 1
        title = tag("h4", b.inline(group["title"]), class_="ck-group") if group.get("title") else ""
        groups += title + tag("ul", items, class_="ck-list")
    key = str(block.get("key") or block.get("title") or f"checklist-{b.counter}")
    fid = b.register({"type": "checklist", "key": str(b.plain_text(key)), "count": count})
    meter = tag(
        "div",
        tag("span", class_="ck-count")
        + tag("span", tag("i", class_="ck-fill"), class_="ck-bar", aria_hidden="true"),
        class_="ck-meter",
        aria_live="polite",
    )
    return tag(
        "figure",
        b.heading(block) + meter + groups,
        class_="fig checklist col",
        data_fig=fid,
    )


RENDERERS: dict[str, Callable[[Builder, Block], str]] = {"quiz": quiz, "checklist": checklist}
