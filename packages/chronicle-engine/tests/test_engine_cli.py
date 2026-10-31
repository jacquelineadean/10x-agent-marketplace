"""The engine's command line with no plugin registered, run in its own process."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = ROOT / "packages" / "chronicle-engine" / "src"
DIAGRAM = ROOT / "plugins" / "chronicle" / "examples" / "animation-diagram"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    """`python -m chronicle_engine` with only the engine importable: no pack registers."""
    env = {**os.environ, "PYTHONPATH": str(ENGINE_SRC)}
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments the test builds
        [sys.executable, "-m", "chronicle_engine", *args],
        capture_output=True,
        text=True,
        env=env,
        check=False,
        timeout=120,
    )


def _story(tmp: Path, **extra: Any) -> Path:
    story = {
        "schema_version": 1,
        "meta": {"title": "Plain page", "dek": "A page with {{team.size}} people."},
        "theme": {"concept": "A plain test page."},
        "chapters": [
            {
                "id": "one",
                "title": "One chapter",
                "blocks": [{"type": "prose", "text": "Text with {{team.size}} people."}],
            }
        ],
        **extra,
    }
    facts = {"team": {"size": {"value": 4, "unit": "people", "source": "test"}}}
    (tmp / "story.json").write_text(json.dumps(story), encoding="utf-8")
    (tmp / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    return tmp / "story.json"


def test_engine_builds_a_story_with_no_art(tmp_path: Path) -> None:
    path = _story(tmp_path)
    result = _run("build", str(path), "--out", str(tmp_path / "build"))
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "build" / "index.html").read_text(encoding="utf-8")
    assert "Plain page" in page
    assert "4 people" in page


def test_engine_refuses_art_with_a_message(tmp_path: Path) -> None:
    path = _story(tmp_path, art={"hero": {"preset": "bridge-hero"}})
    result = _run("check", str(path))
    assert result.returncode == 1
    assert "this plugin makes none" in result.stderr


def test_engine_has_no_paint_or_plugin_commands(tmp_path: Path) -> None:
    path = _story(tmp_path)
    for args in (("paint", str(path)), ("motifs",)):
        result = _run(*args)
        assert result.returncode == 2
        assert "invalid choice" in result.stderr


def test_engine_builds_a_diagram_animation(tmp_path: Path) -> None:
    out = tmp_path / "build"
    result = _run(
        "animate", "build", str(DIAGRAM / "animation.json"), "--out", str(out), "--formats", "svg"
    )
    assert result.returncode == 0, result.stderr
    assert (out / "animation.svg").read_text(encoding="utf-8").startswith("<svg")


def test_engine_knows_only_the_diagram_kind(tmp_path: Path) -> None:
    result = _run("animate", "new", str(tmp_path / "flow"), "--kind", "tad")
    assert result.returncode == 2
    assert "invalid choice" in result.stderr
    made = _run("animate", "new", str(tmp_path / "flow"))
    assert made.returncode == 0, made.stderr
    anim = json.loads((tmp_path / "flow" / "animation.json").read_text(encoding="utf-8"))
    assert anim["kind"] == "diagram"
    assert (tmp_path / "flow" / "drawing.svg").exists()
