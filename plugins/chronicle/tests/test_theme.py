from __future__ import annotations

import json
from typing import Any

import pytest
from chronicle.connectors.files import store
from chronicle.core.story import theme

FONTS: dict[str, Any] = json.loads(store.asset("fonts.json"))


def tokens(css: str, block: int) -> dict[str, str]:
    """Custom properties of the nth rule block in the theme CSS."""
    body = css.split("{")[block + 1].split("}")[0]
    out = {}
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("--") and ":" in line:
            key, value = line.split(":", 1)
            out[key] = value.strip().rstrip(";")
    return out


def test_default_theme_matches_the_original_look() -> None:
    t = theme.build(None, FONTS)
    light = tokens(t.css, 0)
    assert light["--accent"] == "#3358B5"
    assert light["--f-display"].startswith('"Instrument Serif"')
    assert t.progress["kind"] == "arches"
    assert t.mark["style"] == "arch"
    assert t.number(3) == "IV"
    assert "Caveat" not in t.fonts_url  # hand font loads only when a painting uses it


def test_text_colors_are_pushed_until_they_read() -> None:
    pale = "#E2B54A"
    t = theme.build({"palette": {"accent": pale}}, FONTS)
    light = tokens(t.css, 0)
    assert light["--accent"] == pale
    assert theme.contrast(light["--accent-text"], light["--paper"]) >= 4.5
    dark = tokens(t.css, 2)
    assert theme.contrast(dark["--accent"], dark["--paper"]) >= 4.5
    assert theme.contrast(dark["--ink"], dark["--paper"]) >= 7


def test_named_colors_fonts_marks_and_progress_come_through() -> None:
    t = theme.build(
        {
            "palette": {"colors": {"kraft": "#C49A6C"}},
            "fonts": {"display": "Fraunces", "ui": "Barlow"},
            "progress": {"kind": "track", "icon": "parcel", "line": "belt"},
            "chapter_mark": {"style": "label", "format": "padded", "prefix": "No."},
            "stats": "receipt",
        },
        FONTS,
        frozenset({"hand"}),
    )
    assert "--c-kraft: #C49A6C;" in t.css
    assert ".f-kraft { fill: var(--c-kraft); }" in t.css
    assert "family=Fraunces:" in t.fonts_url and "family=Caveat:" in t.fonts_url
    assert "family=IBM+Plex+Mono" in t.fonts_url  # the receipt is set in mono
    assert t.number(0) == "01"
    assert t.progress == {"kind": "track", "icon": "parcel", "line": "belt"}


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"palette": {"accent": "blue"}}, "#rrggbb"),
        ({"palette": {"ink": "#BBBBBB"}}, "contrast"),
        ({"palette": {"paper": "#202020", "ink": "#FFFFFF"}}, "light color"),
        ({"fonts": {"display": "Comic Sans MS"}}, "not in the font list"),
        ({"fonts": {"script": "Caveat"}}, "roles are"),
        ({"progress": {"kind": "spinner"}}, "progress.kind"),
        ({"progress": {"icon": "unicorn"}}, "progress.icon"),
        ({"chapter_mark": "ribbon"}, "chapter_mark.style"),
        ({"stats": "neon"}, "theme.stats"),
        ({"palette": {"colors": {"Bad Name": "#123456"}}}, "lowercase"),
    ],
)
def test_bad_themes_say_what_to_change(spec: dict[str, Any], message: str) -> None:
    with pytest.raises(theme.ThemeError, match=message):
        theme.build(spec, FONTS)


def test_every_listed_font_names_its_kind_and_roles() -> None:
    kinds = {"serif", "sans", "hand", "mono"}
    roles = {"display", "body", "ui", "hand", "mono"}
    for family, entry in FONTS.items():
        assert entry["kind"] in kinds, family
        assert set(entry["roles"]) <= roles, family
