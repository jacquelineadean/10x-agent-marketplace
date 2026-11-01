"""Run the engine with no plugin registered, in its own process, and write small stories."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
ENGINE_SRC = ROOT / "packages" / "chronicle-engine" / "src"
ENGINE = ENGINE_SRC / "chronicle_engine"
DIAGRAM_SVG = (
    '<svg viewBox="0 0 200 60"><rect id="a" class="box" x="4" y="4" width="80" height="40"/>'
    '<text x="12" y="28">Cart</text></svg>'
)


def run(*args: str) -> subprocess.CompletedProcess[str]:
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


def write_story(tmp: Path, blocks: list[dict[str, Any]] | None = None, **extra: Any) -> Path:
    """A one-chapter story with a sourced fact; `blocks` replaces its one prose block."""
    story = {
        "schema_version": 1,
        "meta": {"title": "Plain page", "dek": "A page with {{team.size}} people."},
        "theme": {"concept": "A plain test page."},
        "chapters": [
            {
                "id": "one",
                "title": "One chapter",
                "blocks": blocks or [{"type": "prose", "text": "Text with {{team.size}} people."}],
            }
        ],
        **extra,
    }
    facts = {"team": {"size": {"value": 4, "unit": "people", "source": "test"}}}
    (tmp / "story.json").write_text(json.dumps(story), encoding="utf-8")
    (tmp / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    return tmp / "story.json"


def build(tmp: Path, blocks: list[dict[str, Any]] | None = None, **extra: Any) -> str:
    """Build a story with the engine alone and return its standalone page."""
    path = write_story(tmp, blocks, **extra)
    result = run("build", str(path), "--out", str(tmp / "build"))
    if result.returncode != 0:
        raise AssertionError(f"build failed: {result.stderr}")
    return (tmp / "build" / "index.html").read_text(encoding="utf-8")
