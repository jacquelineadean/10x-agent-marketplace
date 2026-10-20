from __future__ import annotations

import json
from pathlib import Path
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


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ({"progress": {"kind": "route"}}, "route needs a path"),
        ({"progress": {"kind": "route", "path": "M0,0 L10,10<script>"}}, "SVG path data"),
        ({"progress": {"icon_path": "L0,0 L4,4"}}, "starting with M"),
        ({"surface": {"texture": "marble"}}, "surface.texture"),
        ({"surface": {"lighting": "warm"}}, "surface.lighting is unknown"),
        ({"words": {"chapter": "Hole"}}, "words.chapter is unknown"),
        ({"words": {"question": "<b>Hole</b>"}}, "plain text"),
    ],
)
def test_new_theme_parts_say_what_to_change(spec: dict[str, Any], message: str) -> None:
    with pytest.raises(theme.ThemeError, match=message):
        theme.build(spec, FONTS)


def test_route_icon_surface_and_words_come_through() -> None:
    t = theme.build(
        {
            "progress": {
                "kind": "route",
                "path": "M0,30  C200,0 800,40 1000,10",
                "icon_path": "M-3,8 L0,-8 L3,8 Z",
            },
            "surface": {"texture": "ruled", "corners": "square", "frame": "tape"},
            "words": {"question": "Hole", "sources": "Field notes"},
        },
        FONTS,
    )
    assert t.progress["path"] == "M0,30 C200,0 800,40 1000,10"
    assert t.progress["icon_path"] == "M-3,8 L0,-8 L3,8 Z"
    assert "--round: 0;" in t.css
    assert "background-size: 100% 2rem" in t.css
    assert ".plate .frame::before" in t.css
    assert t.words["question"] == "Hole" and t.words["sources"] == "Field notes"
    assert t.words["next"] == "Next"


def test_review_flags_a_missing_or_stock_theme() -> None:
    assert "theme is missing" in theme.review(None, {})[0]
    warnings = theme.review({"palette": {"paper": "#FBFAF6"}}, {})
    assert any("theme.concept is empty" in w for w in warnings)
    assert any("chronicle's defaults for type, accent" in w for w in warnings)


def test_review_flags_a_page_that_copies_another() -> None:
    golf = {
        "concept": "a yardage book",
        "palette": {"accent": "#2E6B3C", "paper": "#F7F5EE"},
        "fonts": {"display": "Fraunces", "body": "Lora"},
        "progress": {"kind": "flags"},
        "chapter_mark": "flag",
    }
    copy = {**golf, "concept": "a fishing guide", "palette": {"accent": "#2F6D3E"}}
    assert theme.likeness(golf, copy) == [
        "type",
        "accent",
        "paper",
        "progress device",
        "chapter mark",
        "stat panel",
    ]
    assert any("looks like golf" in w for w in theme.review(copy, {"golf": golf}))
    other = {
        **copy,
        "palette": {"accent": "#8A3B12", "paper": "#EEF2F4"},
        "fonts": {"display": "Gloock", "body": "Literata"},
        "stats": "cards",
    }
    assert not any("looks like" in w for w in theme.review(other, {"golf": golf}))


def test_the_bundled_examples_do_not_look_alike() -> None:
    root = Path(__file__).resolve().parents[1] / "examples"
    themes = {p.parent.name: store.read_json(p)["theme"] for p in root.glob("*/story.json")}
    assert len(themes) == 3
    for name, spec in themes.items():
        others = {k: v for k, v in themes.items() if k != name}
        assert theme.review(spec, others) == [], name
