"""chronicle's registrations restore everything the plugin offered before the engine split."""

from __future__ import annotations

import chronicle.pack  # noqa: F401  (registers chronicle's blocks, art, kinds and commands)
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
    assert list(registry.KINDS) == ["scene", "diagram", "tad"]
    assert list(registry.COMMANDS) == ["motifs"]
    assert registry.art() is not None
    assert registry.DEFAULTS.prog == "chronicle"
    assert registry.DEFAULTS.policy == "distinct"
    assert registry.DEFAULTS.kind == "tad"
    assert registry.DEFAULTS.new_folders == ("art", "diagrams", "widgets")
    assert "distinct" in registry.POLICIES
