from __future__ import annotations

import json
import shutil
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
    assert manifest["hero"]["width"] == 1600
    assert manifest["hero"]["layers"][0]["name"] == "steam"
    assert any(label["style"] == "hand" for label in manifest["hero"]["labels"])


def test_bad_story_fails_with_a_message(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "keystone"
    shutil.copytree(example_dir, copy, ignore=shutil.ignore_patterns("build"))
    story = json.loads((copy / "story.json").read_text(encoding="utf-8"))
    story["chapters"][0]["title"] = "Up {{nowhere.at_all}}"
    path = copy / "story.json"
    path.write_text(json.dumps(story), encoding="utf-8")
    code = main(["check", str(path)])
    assert code == 1
    assert "no fact 'nowhere.at_all'" in capsys.readouterr().err


def test_second_example_uses_no_bridge_scenes(example_dir: Path, tmp_path: Path) -> None:
    quarterly = example_dir.parent / "quarterly" / "story.json"
    assert main(["check", str(quarterly)]) == 0
    assert main(["build", str(quarterly), "--out", str(tmp_path), "--scale", "0.12"]) == 0
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert "<title>Lantern Bay</title>" in page
    assert "12,501" in page


def test_onboarding_example_builds_its_widget_quiz_and_checklist(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    story = example_dir.parent / "onboarding" / "story.json"
    assert main(["check", str(story)]) == 0
    assert "0 warning(s)" in capsys.readouterr().out
    assert main(["build", str(story), "--out", str(tmp_path), "--scale", "0.12"]) == 0
    page = (tmp_path / "index.html").read_text(encoding="utf-8")
    assert '["dial-in"] = function (root, data, kit) {' in page
    assert 'class="fig quiz' in page
    assert 'class="fig checklist' in page
    assert "garage in <span" in page  # the founding year is a token, printed as 2014
    assert ">2014<" in page
