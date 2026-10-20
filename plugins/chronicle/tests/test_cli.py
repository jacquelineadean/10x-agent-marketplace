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


def test_runtime_carries_no_copy_from_one_example() -> None:
    from chronicle.connectors.files import store

    runtime = store.asset_parts("js", ".js") + store.asset_parts("css", ".css")
    for word in ("Keystone", "monolith", "Monolith", "ultramarine", "last arch"):
        assert word not in runtime, word


def test_new_starts_a_run_folder_kept_out_of_git(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".git").mkdir()
    (tmp_path / ".gitignore").write_text("node_modules/", encoding="utf-8")
    assert main(["new", "chronicle-runs/q4", "--title", "Q4 review"]) == 0
    story = json.loads((tmp_path / "chronicle-runs/q4/story.json").read_text(encoding="utf-8"))
    assert story["meta"]["title"] == "Q4 review"
    assert story["theme"] == {"concept": ""}
    assert (tmp_path / ".gitignore").read_text(
        encoding="utf-8"
    ) == "node_modules/\nchronicle-runs/\n"
    assert main(["check", "chronicle-runs/q4/story.json"]) == 0
    assert "theme.concept is empty" in capsys.readouterr().err
    assert main(["new", "chronicle-runs/q4"]) == 1


def test_check_warns_when_a_run_copies_an_example(
    example_dir: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    copy = tmp_path / "runs" / "mine"
    shutil.copytree(example_dir, copy, ignore=shutil.ignore_patterns("build"))
    assert main(["check", str(copy / "story.json")]) == 0
    assert "theme looks like example keystone" in capsys.readouterr().err


def test_shoot_opens_the_still_page_at_desktop_and_phone_width(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import subprocess

    from chronicle.connectors.browser import shoot

    (tmp_path / "build").mkdir()
    (tmp_path / "build" / "index.html").write_text("<p>page</p>", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(args: list[str], **_: object) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        out = next(a for a in args if a.startswith("--screenshot=")).split("=", 1)[1]
        Path(out).write_bytes(b"png")
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(shoot.subprocess, "run", fake_run)
    story = tmp_path / "story.json"
    assert main(["shoot", str(story), "--browser", "/bin/sh"]) == 0
    assert calls[0][-1].endswith("build/index.html#still")
    assert "--window-size=1280,2400" in calls[0]
    assert "--window-size=500,2000" in calls[1]
    holder = (tmp_path / "build" / "shots" / "phone.html").read_text(encoding="utf-8")
    assert 'width="390"' in holder and "index.html#still" in holder
    assert (tmp_path / "build" / "shots" / "desktop.png").exists()


def test_shoot_without_a_build_or_browser_says_so(tmp_path: Path) -> None:
    from chronicle.connectors.browser import shoot

    assert main(["shoot", str(tmp_path / "story.json")]) == 1
    with pytest.raises(shoot.BrowserError, match="no Chromium"):
        shoot.find(str(tmp_path / "no-such-browser"))
