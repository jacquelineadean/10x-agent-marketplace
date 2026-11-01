"""Filters over precomputed slices: a block marked `slice` renders once per option.

The `filters` block names each filter and its options. A block with `"slice": "team"`
writes `{team}` where a fact path changes with the option, such as
`{{delivery.{team}.deploys}}`; the build renders one copy per option and the page shows
the chosen one. Nothing is computed in the browser.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

from chronicle_engine.core.story.dispatch import render_block
from chronicle_engine.core.story.html import tag
from chronicle_engine.core.story.markup import plain
from chronicle_engine.core.story.render import Builder

REQUIRED = ("by",)
OPTIONAL = ("title",)


def filters_of(story: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Every filter the story's filters blocks define, by key."""
    found: dict[str, dict[str, Any]] = {}
    for chapter in story.get("chapters", []):
        for block in chapter.get("blocks", []):
            if isinstance(block, Mapping) and block.get("type") == "filters":
                for spec in block.get("by", []):
                    if isinstance(spec, Mapping) and spec.get("key"):
                        found[str(spec["key"])] = dict(spec)
    return found


def options(spec: Mapping[str, Any]) -> list[str]:
    return [str(k) for k in dict(spec.get("options") or {})]


def default(spec: Mapping[str, Any]) -> str:
    keys = options(spec)
    return str(spec.get("default") or (keys[0] if keys else ""))


def substitute(node: Any, key: str, option: str) -> Any:
    """The block with `{key}` replaced by the option in every string."""
    if isinstance(node, str):
        return node.replace("{" + key + "}", option)
    if isinstance(node, Mapping):
        return {k: substitute(v, key, option) for k, v in node.items()}
    if isinstance(node, list):
        return [substitute(v, key, option) for v in node]
    return node


def variants(
    block: Mapping[str, Any], spec: Mapping[str, Any]
) -> Iterator[tuple[str, dict[str, Any]]]:
    """Each option and the block as it reads for that option, without `slice` or `id`."""
    key = str(block["slice"])
    for option in options(spec):
        copy = substitute({k: v for k, v in block.items() if k not in ("slice", "id")}, key, option)
        yield option, copy


def render(b: Builder, block: Mapping[str, Any], found: Mapping[str, Mapping[str, Any]]) -> str:
    """A block, or one copy per option of its filter with all but the default hidden."""
    key = block.get("slice")
    if not key:
        return render_block(b, block)
    spec = found[str(key)]
    chosen = default(spec)
    return "".join(
        tag(
            "div",
            render_block(b, copy),
            class_="slice",
            data_slice=str(key),
            data_option=option,
            hidden=option != chosen,
        )
        for option, copy in variants(block, spec)
    )


def filters(b: Builder, block: Mapping[str, Any]) -> str:
    """The filter controls; the page script shows the slices that match."""
    controls = ""
    for spec in block["by"]:
        key = str(spec["key"])
        labels = dict(spec.get("options") or {})
        chosen = default(spec)
        opts = "".join(
            tag("option", plain(str(label)), value=k, selected=k == chosen)
            for k, label in labels.items()
        )
        controls += tag(
            "label",
            tag("span", plain(str(spec.get("label", key))), class_="filter-label")
            + tag("select", opts, data_filter=key),
            class_="filter",
        )
    fid = b.register({"type": "filters", "keys": [str(s["key"]) for s in block["by"]]})
    title = (
        tag("h3", b.inline(block["title"]), class_="filters-title") if block.get("title") else ""
    )
    return tag(
        "div",
        title + tag("div", controls, class_="filter-row"),
        class_="filters wide",
        data_fig=fid,
    )
