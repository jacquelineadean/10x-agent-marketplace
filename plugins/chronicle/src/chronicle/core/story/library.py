"""The widget library: drills written once and reused across runs.

A library widget is a folder named for the widget: `widget.js` (the body of the widget
function, as for any widget), an optional `widget.css`, and `widget.json` with its
title, what it does, example data and fallback text. Folders are searched in order: the
repository's `.chronicle/widgets/`, the user's config folder, then the ones chronicle
ships. `chronicle widgets add` copies one into a run folder and prints its block.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

NAME = re.compile(r"^[a-z][a-z0-9-]{1,30}$")
WHERE = ("repo", "config", "bundled")


def check_meta(name: str, meta: Any) -> list[str]:
    """Problems with a widget's name and widget.json."""
    problems = [] if NAME.match(name) else [f"{name!r} must be lowercase letters, digits and -"]
    if not isinstance(meta, Mapping):
        return [*problems, "widget.json must hold an object"]
    for key in ("title", "summary", "fallback"):
        if not str(meta.get(key, "")).strip():
            problems.append(f"widget.json needs {key}")
    if not isinstance(meta.get("data"), Mapping):
        problems.append("widget.json needs data: an example of what the script reads")
    return problems


def block(name: str, meta: Mapping[str, Any], styled: bool) -> dict[str, Any]:
    """The story block for a copied widget, filled with its example data."""
    out: dict[str, Any] = {
        "type": "widget",
        "name": name,
        "title": str(meta["title"]),
        "subtitle": str(meta["summary"]),
        "script": f"widgets/{name}.js",
    }
    if styled:
        out["style"] = f"widgets/{name}.css"
    out["data"] = dict(meta["data"])
    out["fallback"] = str(meta["fallback"])
    return out


def meta_from(block_spec: Mapping[str, Any], summary: str) -> dict[str, Any]:
    """widget.json for a run's widget, from its story block."""
    return {
        "title": str(block_spec.get("title", "")),
        "summary": summary or str(block_spec.get("subtitle", "")),
        "data": dict(block_spec.get("data") or {}),
        "fallback": str(block_spec.get("fallback", "")),
    }
