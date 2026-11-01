"""The sameness review: chronicle's `distinct` policy, so no two pages look alike.

`chronicle check` compares a page's theme with the bundled examples and sibling run
folders and warns when it keeps the defaults or shares three features with another page.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.theme import DEFAULT_FONTS, LIGHT, hex_rgb

HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def review(spec: Mapping[str, Any] | None, others: Mapping[str, Any]) -> list[str]:
    """Warnings for a theme that looks generic or like another page.

    `others` maps a page's name (an example, another run) to its theme. A page shares a
    feature with another when both pick the same fonts, a close accent or paper, the same
    progress device, chapter mark or stat panel; three shared features read as the same page.
    """
    spec = dict(spec or {})
    if not spec:
        return [
            "theme is missing, so the page gets chronicle's placeholder look; "
            "do the design pass in references/identity.md"
        ]
    out = []
    if not str(spec.get("concept", "")).strip():
        out.append(
            "theme.concept is empty; name the world the page borrows from and what it was "
            "taken from (the user's brand, the request's words, the material)"
        )
    mine = _features(spec)
    defaults = _features({})
    stock = [name for name, value in mine.items() if value == defaults[name] and value]
    if len(stock) >= 2:
        out.append(
            f"theme keeps chronicle's defaults for {', '.join(stock)}; pick them from the subject"
        )
    for name, other in sorted(others.items()):
        shared = likeness(spec, other if isinstance(other, Mapping) else {})
        if len(shared) >= 3:
            out.append(f"theme looks like {name}: same {', '.join(shared)}; change at least two")
    return out


def likeness(a: Mapping[str, Any], b: Mapping[str, Any]) -> list[str]:
    """The identity features two themes share."""
    fa, fb = _features(dict(a or {})), _features(dict(b or {}))
    shared = []
    for name in fa:
        va, vb = fa[name], fb[name]
        if name in ("accent", "paper"):
            if _near(str(va), str(vb), 0.06 if name == "accent" else 0.025):
                shared.append(name)
        elif va == vb:
            shared.append(name)
    return shared


def _features(spec: Mapping[str, Any]) -> dict[str, str]:
    palette = dict(spec.get("palette", {}) or {})
    fonts = {**DEFAULT_FONTS, **dict(spec.get("fonts", {}) or {})}
    progress = dict(spec.get("progress", {}) or {})
    kind = str(progress.get("kind", "arches"))
    device = f"{kind}/{progress.get('icon', 'dot')}" if kind in ("track", "route") else kind
    mark = spec.get("chapter_mark", {})
    style = mark if isinstance(mark, str) else dict(mark or {}).get("style", "arch")
    return {
        "type": f"{fonts['display']} + {fonts['body']}",
        "accent": str(palette.get("accent", LIGHT["accent"])).upper(),
        "paper": str(palette.get("paper", LIGHT["paper"])).upper(),
        "progress device": device,
        "chapter mark": str(style),
        "stat panel": str(spec.get("stats", "rule")),
    }


def _near(a: str, b: str, limit: float) -> bool:
    if not (HEX.match(a) and HEX.match(b)):
        return a == b
    ra, rb = hex_rgb(a), hex_rgb(b)
    distance: float = sum((x - y) ** 2 for x, y in zip(ra, rb, strict=True)) ** 0.5
    return distance / 3**0.5 < limit
