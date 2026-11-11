"""The solutions block: a solutions file on a page, where a reader moves inputs and
settings, switches scenarios, adds variants, feels a wait and exports a decision.

The static table shows every approach at its own settings in the first scenario, so the
page reads without scripts; the page's script replaces it with the controls.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Builder

from blueprint.core.solutions import digest, simulate

REQUIRED = ("file",)
OPTIONAL = ("title", "subtitle", "source")


def solutions(b: Builder, block: Mapping[str, Any]) -> str:
    path = str(block["file"])
    found = simulate.run(str(b.files.get(path, "")), b.facts, Report())
    if found is None:
        # The check refuses a file with errors, so a build never reaches this.
        return ""
    spec = found.spec
    fid = b.register({"type": "solutions", **spec, "expect": found.results, "file": path})
    first = spec["scenarios"][0]
    head = tag("th", "Approach", scope="col") + "".join(
        tag("th", b.inline(m["label"]), scope="col") for m in spec["measures"]
    )
    rows = "".join(
        tag(
            "tr",
            tag("th", b.inline(a["label"]), scope="row")
            + "".join(
                tag("td", plain(digest.show(found.results[first["id"]][a["id"]][m["id"]], m)))
                for m in spec["measures"]
            ),
        )
        for a in spec["approaches"]
    )
    table = tag(
        "table",
        tag("caption", b.inline(first["label"]) + ", each approach at its own settings")
        + tag("thead", tag("tr", head))
        + tag("tbody", rows),
    )
    about = "".join(
        tag("dt", b.inline(a["label"])) + tag("dd", b.inline(a["text"])) for a in spec["approaches"]
    )
    heading = {"title": block.get("title") or spec["title"], "subtitle": block.get("subtitle", "")}
    return tag(
        "figure",
        b.heading(heading)
        + tag("p", b.inline(spec["question"]), class_="sol-question")
        + tag("div", class_="sol-app", hidden=True)
        + tag(
            "div", tag("div", table, class_="table-scroll") + tag("dl", about), class_="sol-static"
        )
        + b.source_line(block, table=False),
        class_="fig solutions wide",
        data_fig=fid,
    )
