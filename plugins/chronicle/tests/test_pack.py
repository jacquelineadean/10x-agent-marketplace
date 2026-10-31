"""chronicle's registrations restore everything the plugin offered before the engine split."""

from __future__ import annotations

import chronicle.pack  # noqa: F401  (registers chronicle's blocks, art, kinds and commands)
from chronicle.core.story import chrome
from chronicle_engine import registry
from chronicle_engine.core.story import model


def test_block_types_keep_their_order() -> None:
    assert list(model.BLOCKS) == [
        "prose",
        "stats",
        "lesson",
        "quote",
        "chart",
        "scrolly",
        "timeline",
        "stepper",
        "compare",
        "matrix",
        "roadmap",
        "team",
        "model",
        "table",
        "plate",
        "tilemap",
        "flow",
        "diagram",
        "quiz",
        "checklist",
        "widget",
    ]


def test_kinds_commands_and_defaults() -> None:
    assert list(registry.KINDS) == ["scene", "diagram"]
    assert list(registry.COMMANDS) == ["motifs", "research"]
    assert registry.art() is not None
    assert registry.DEFAULTS.prog == "chronicle"
    assert registry.DEFAULTS.policy == "distinct"
    assert registry.DEFAULTS.kind == "scene"
    assert registry.DEFAULTS.new_folders == ("art", "diagrams", "widgets")
    assert "distinct" in registry.POLICIES


def test_chrome_keeps_its_choices_order_and_defaults() -> None:
    table = registry.CHROME
    assert list(table.progress) == ["arches", "track", "route", "tape", "flags", "clock", "steps"]
    assert [kind for kind, path in table.progress.items() if path] == ["route"]
    assert table.lines == ["solid", "dashed", "belt", "road", "rail"]
    assert list(table.marks) == [
        "arch",
        "label",
        "tag",
        "sign",
        "badge",
        "flag",
        "plain",
        "step",
        "none",
    ]
    assert table.marks["arch"] == "roman" and table.marks["tag"] == "decimal"
    assert list(table.stats) == ["rule", "receipt", "cards", "ticket"]
    assert [name for name, skin in table.stats.items() if skin.paper] == ["receipt", "ticket"]
    assert list(table.frames) == ["none", "mat", "tape"]
    assert (table.progress_default, table.mark_default) == ("arches", "arch")


def test_registering_the_chrome_again_changes_nothing() -> None:
    before = (
        dict(registry.CHROME.progress),
        list(registry.CHROME.lines),
        dict(registry.CHROME.marks),
        dict(registry.CHROME.stats),
        dict(registry.CHROME.frames),
        list(registry.ALWAYS),
    )
    chrome.register()
    after = (
        dict(registry.CHROME.progress),
        list(registry.CHROME.lines),
        dict(registry.CHROME.marks),
        dict(registry.CHROME.stats),
        dict(registry.CHROME.frames),
        list(registry.ALWAYS),
    )
    assert after == before


def test_pages_ship_the_chrome_and_painted_pages_ship_the_plate_parts() -> None:
    plain = registry.page_parts(["chart"])
    assert set(chrome.PARTS) <= set(plain)
    assert "js/30-plates.js" not in plain and "css/11-plates.css" not in plain
    painted = registry.page_parts(["plate"])
    assert {"js/30-plates.js", "css/11-plates.css", "css/40-drawn.css"} <= set(painted)
    assert painted == sorted(painted)
