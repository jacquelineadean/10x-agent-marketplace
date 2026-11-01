"""The ids blocks carry, and the keys under which a page keeps records on the device."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

ID = re.compile(r"^[a-z][a-z0-9-]{0,40}$")


def stored(story: Mapping[str, Any], kind: str, given: Any = None) -> str:
    """`chronicle-<kind>:<given>`; without a given key, the page title's slug stands in."""
    if not given:
        title = str(story.get("meta", {}).get("title", "page"))
        given = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "page"
    return f"chronicle-{kind}:{given}"
