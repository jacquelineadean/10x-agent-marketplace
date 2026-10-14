from __future__ import annotations

import json
from pathlib import Path

import pytest
from chronicle.entrypoints.cli.main import main


def test_check_passes_the_example(example_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["check", str(example_dir / "story.json")]) == 0
    assert "0 warning(s)" in capsys.readouterr().out


def test_build_paints_and_writes_both_pages(example_dir: Path, tmp_path: Path) -> None:
    code = main(
        ["build", str(example_dir / "story.json"), "--out", str(tmp_path), "--scale", "0.12"]
    )
    assert code == 0
    fragment = (tmp_path / "artifact.html").read_text(encoding="utf-8")
    assert "<!doctype" not in fragment
    assert (tmp_path / "index.html").read_text(encoding="utf-8").startswith("<!doctype html>")
    files = json.loads((tmp_path / "publish-files.json").read_text(encoding="utf-8"))
    assert "art/hero.webp" in files
    assert all((tmp_path / rel).exists() for rel in files)
    manifest = json.loads((tmp_path / "art" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["hero"]["width"] == 1800


def test_bad_story_fails_with_a_message(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    story = json.loads((example_dir / "story.json").read_text(encoding="utf-8"))
    story["chapters"][0]["title"] = "Up {{nowhere.at_all}}"
    path = tmp_path / "story.json"
    path.write_text(json.dumps(story), encoding="utf-8")
    code = main(["check", str(path), "--facts", str(example_dir / "facts.json")])
    assert code == 1
    assert "no fact 'nowhere.at_all'" in capsys.readouterr().err
