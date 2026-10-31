"""A brand kit: an organization's colors and type, applied to every page it builds.

The kit fills the theme where the story is silent, so a team's decks, dashboards and
pages share one look. A story may still set its own values; `departures` lists each one
so `check` can warn that the page leaves the kit.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.theme import DEFAULT_FONTS, ThemeError

SCHEMA_VERSION = 1
FIELDS = ("schema_version", "name", "palette", "dark", "fonts")
PALETTE = ("paper", "ink", "accent", "legacy", "good", "warn", "bad", "series", "colors")
DARK = ("paper", "ink", "accent", "legacy")
MERGED = ("palette", "dark", "fonts")


def check_kit(kit: Any) -> dict[str, Any]:
    """The kit as a dict; raises ThemeError naming the field to fix."""
    if not isinstance(kit, Mapping):
        raise ThemeError("a brand kit must be a JSON object")
    for key in kit:
        if key not in FIELDS:
            raise ThemeError(f"brand kit field {key!r} is unknown; use {', '.join(FIELDS)}")
    if kit.get("schema_version", SCHEMA_VERSION) != SCHEMA_VERSION:
        raise ThemeError(f"brand kit schema_version must be {SCHEMA_VERSION}")
    for section, allowed in (("palette", PALETTE), ("dark", DARK), ("fonts", tuple(DEFAULT_FONTS))):
        values = kit.get(section, {})
        if not isinstance(values, Mapping):
            raise ThemeError(f"brand kit {section} must be an object")
        for key in values:
            if key not in allowed:
                raise ThemeError(f"brand kit {section}.{key} is unknown; use {', '.join(allowed)}")
    return dict(kit)


def apply(theme: Mapping[str, Any] | None, kit: Mapping[str, Any]) -> dict[str, Any]:
    """The story's theme with the kit's palette, dark colors and fonts underneath it."""
    merged = dict(theme or {})
    for section in MERGED:
        if kit.get(section):
            merged[section] = {**kit[section], **dict(merged.get(section) or {})}
    return merged


def departures(theme: Mapping[str, Any] | None, kit: Mapping[str, Any]) -> list[str]:
    """Each theme value that overrides the kit, as a warning."""
    out = []
    own = theme or {}
    name = str(kit.get("name") or "the brand kit")
    for section in MERGED:
        mine = own.get(section) or {}
        for key, value in dict(kit.get(section) or {}).items():
            if key in mine and mine[key] != value:
                out.append(f"theme.{section}.{key} {mine[key]!r} departs from {name}'s {value!r}")
    return out
