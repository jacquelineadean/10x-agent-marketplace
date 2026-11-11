"""The engine's command line with no plugin registered, run in its own process."""

from __future__ import annotations

import json
from pathlib import Path

from engine_helpers import ROOT, run, write_story

DIAGRAM = ROOT / "plugins" / "chronicle" / "examples" / "animation-diagram"


def test_engine_builds_a_story_with_no_art(tmp_path: Path) -> None:
    path = write_story(tmp_path)
    result = run("build", str(path), "--out", str(tmp_path / "build"))
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "build" / "index.html").read_text(encoding="utf-8")
    assert "Plain page" in page
    assert "4 people" in page


def test_engine_refuses_art_with_a_message(tmp_path: Path) -> None:
    path = write_story(tmp_path, art={"hero": {"preset": "bridge-hero"}})
    result = run("check", str(path))
    assert result.returncode == 1
    assert "this plugin makes none" in result.stderr


def test_engine_has_no_paint_or_plugin_commands(tmp_path: Path) -> None:
    path = write_story(tmp_path)
    for args in (("paint", str(path)), ("motifs",), ("research", str(tmp_path))):
        result = run(*args)
        assert result.returncode == 2
        assert "invalid choice" in result.stderr


def test_engine_builds_a_diagram_animation(tmp_path: Path) -> None:
    out = tmp_path / "build"
    result = run(
        "animate", "build", str(DIAGRAM / "animation.json"), "--out", str(out), "--formats", "svg"
    )
    assert result.returncode == 0, result.stderr
    assert (out / "animation.svg").read_text(encoding="utf-8").startswith("<svg")


def test_engine_knows_only_the_diagram_kind(tmp_path: Path) -> None:
    result = run("animate", "new", str(tmp_path / "flow"), "--kind", "tad")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    made = run("animate", "new", str(tmp_path / "flow"))
    assert made.returncode == 0, made.stderr
    anim = json.loads((tmp_path / "flow" / "animation.json").read_text(encoding="utf-8"))
    assert anim["kind"] == "diagram"
    assert (tmp_path / "flow" / "drawing.svg").exists()
