"""Game scoring: a story's quizzes played as holes, a tally in the page's bar, a scorecard.

With a top-level `game` object, every quiz becomes a hole. Its par is its question count
plus one, unless the block names a `par`. Each answer the reader picks is a stroke; a
wrong pick drops out of the list, and the reader picks again. Strokes against par name
the hole (birdie, par, bogey). The page's bar gains a flag per hole, colored by its
result, and a `scorecard` block totals the round. Without `game`, a quiz is a quiz.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from chronicle_engine.core.story import lessons
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.render import Builder

NAMES = {
    "-3": "Albatross",
    "-2": "Eagle",
    "-1": "Birdie",
    "0": "Par",
    "1": "Bogey",
    "2": "Double bogey",
    "3": "Triple bogey",
}
ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")

Block = Mapping[str, Any]


def holes(story: Mapping[str, Any]) -> Iterator[tuple[int, str, Block]]:
    """Every hole in story order: its number, the chapter id it sits in, and its block."""
    n = 0
    for chapter in story.get("chapters", []):
        if not isinstance(chapter, Mapping):
            continue
        for block in chapter.get("blocks", []):
            if isinstance(block, Mapping) and block.get("type") == "quiz":
                n += 1
                yield n, str(chapter.get("id", "")), block


def par(block: Block) -> int:
    return int(block.get("par") or len(block.get("questions", [])) + 1)


def hole_id(n: int, block: Block) -> str:
    return str(block.get("id") or f"hole-{n}")


def _settings(b: Builder) -> dict[str, Any]:
    game = b.story.get("game") or {}
    title = str(b.story.get("meta", {}).get("title", "page"))
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "page"
    return {
        "names": {**NAMES, **{str(k): str(v) for k, v in dict(game.get("names") or {}).items()}},
        "key": f"chronicle-game:{game.get('key') or slug}",
    }


def _card_id(story: Mapping[str, Any]) -> str:
    for chapter in story.get("chapters", []):
        for block in chapter.get("blocks", []) if isinstance(chapter, Mapping) else []:
            if isinstance(block, Mapping) and block.get("type") == "scorecard":
                return str(block.get("id") or "scorecard")
    return ""


def quiz(b: Builder, block: Block) -> str:
    """A hole when the story is a game; otherwise the engine's quiz."""
    if not isinstance(b.story.get("game"), Mapping):
        return lessons.quiz(b, block)
    found = [(n, chapter, h) for n, chapter, h in holes(b.story) if h is block]
    n, _, _ = found[0] if found else (0, "", block)
    every = list(holes(b.story))
    later = [hole_id(m, h) for m, _, h in every if m == n + 1]
    card = _card_id(b.story)
    if later:
        follow = {"href": f"#{later[0]}", "label": "Next hole"}
    elif card:
        follow = {"href": f"#{card}", "label": "See your card"}
    else:
        follow = {}
    questions = block.get("questions", [])
    hid = hole_id(n, block)
    fid = b.register(
        {
            "type": "hole",
            "id": hid,
            "no": n,
            "par": par(block),
            "answers": [int(q["answer"]) for q in questions],
            "next": follow,
            **_settings(b),
        }
    )
    items = ""
    for i, q in enumerate(questions):
        options = "".join(
            tag(
                "li",
                tag(
                    "button",
                    tag("span", chr(ord("A") + k), class_="hl-key", aria_hidden="true")
                    + tag("span", b.inline(opt), class_="hl-opt-text"),
                    type="button",
                    class_="hl-opt",
                    data_k=k,
                ),
            )
            for k, opt in enumerate(q.get("options", []))
        )
        items += tag(
            "li",
            tag("p", f"Question {i + 1} of {len(questions)}", class_="hl-count")
            + tag("p", b.inline(q.get("q", "")), class_="hl-text", tabindex="-1")
            + tag("ol", options, class_="hl-opts")
            + tag("div", b.paras(q.get("explain", "")), class_="hl-explain"),
            class_="hl-q",
            data_i=i,
        )
    title = b.inline(block.get("title") or f"Hole {n}")
    meta = tag(
        "dl",
        tag("div", tag("dt", "Par") + tag("dd", str(par(block)), class_="hl-par"))
        + tag("div", tag("dt", "Strokes") + tag("dd", "0", class_="hl-strokes")),
        class_="hl-meta",
    )
    head = tag(
        "header",
        tag("span", str(n), class_="hl-no", aria_hidden="true")
        + tag(
            "div",
            tag("p", f"Hole {n}", class_="hl-kick") + tag("h3", title, class_="hl-name"),
            class_="hl-titles",
        )
        + meta,
        class_="hl-head",
    )
    return tag(
        "section",
        head
        + tag("ol", items, class_="hl-list")
        + tag("p", class_="hl-feedback", aria_live="polite")
        + tag("div", class_="hl-result", hidden=True),
        class_="fig hole col",
        id=hid,
        data_fig=fid,
        aria_label=f"Hole {n}",
    )


def scorecard(b: Builder, block: Block) -> str:
    """The round's card: par and strokes per hole, filled in by the page as holes finish."""
    every = list(holes(b.story))
    rows: list[dict[str, Any]] = [
        {
            "id": hole_id(n, h),
            "no": n,
            "par": par(h),
            "title": str(b.plain_text(str(h.get("title") or f"Hole {n}"))),
        }
        for n, _, h in every
    ]
    fid = b.register({"type": "scorecard", "holes": rows, **_settings(b)})
    head = tag("th", "Hole", scope="col") + "".join(
        tag("th", str(r["no"]), scope="col") for r in rows
    )
    head += tag("th", "Total", scope="col")
    pars = tag("th", "Par", scope="row") + "".join(tag("td", str(r["par"])) for r in rows)
    pars += tag("td", str(sum(par(h) for _, _, h in every)))
    strokes = tag("th", "Strokes", scope="row") + "".join(tag("td", "–") for _ in rows)
    strokes += tag("td", "–")
    table = tag(
        "table",
        tag("thead", tag("tr", head)) + tag("tbody", tag("tr", pars) + tag("tr", strokes)),
        class_="sc-table",
    )
    return tag(
        "figure",
        b.heading(block)
        + tag("div", table, class_="sc-scroll")
        + tag("div", class_="sc-summary", aria_live="polite")
        + b.source_line(block, table=False),
        class_="fig scorecard col",
        id=str(block.get("id") or "scorecard"),
        data_fig=fid,
    )


def check(story: Mapping[str, Any], report: Any) -> None:
    """The game object, hole ids and pars."""
    game = story.get("game")
    if game is None:
        return
    if not isinstance(game, Mapping):
        report.errors.append('game must be an object, such as {} or {"names": {...}}')
        return
    names = game.get("names", {})
    if not isinstance(names, Mapping) or not all(
        re.match(r"^-?\d$", str(k)) and isinstance(v, str) for k, v in names.items()
    ):
        report.errors.append('game.names maps strokes against par ("-1", "0", "1") to words')
    seen: set[str] = set()
    for n, _, block in holes(story):
        where = f"hole {n}"
        hid = hole_id(n, block)
        if not ID.match(hid) or hid in seen:
            report.errors.append(f"{where}: id {hid!r} must be unique, lowercase letters and -")
        seen.add(hid)
        given = block.get("par")
        count = len(block.get("questions", []))
        if given is not None and (not isinstance(given, int) or given < count):
            report.errors.append(f"{where}: par must be a whole number of at least {count}")
    if not seen:
        report.warnings.append("game is set but the story has no quiz to play as a hole")
