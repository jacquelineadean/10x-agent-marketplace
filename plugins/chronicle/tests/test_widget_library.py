"""The widget library: bundled drills, lookup order, copying into a run and saving back."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest
from chronicle.core.story import library
from chronicle.entrypoints.cli import widgets
from chronicle_engine.core.story.model import lint_style, lint_widget

BUNDLED = sorted(p for p in widgets.BUNDLED.iterdir() if p.is_dir())


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A repository of its own and an empty config folder."""
    repo = tmp_path / "repo"
    (repo / ".git").mkdir(parents=True)
    monkeypatch.chdir(repo)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    return repo


def _run(*argv: str) -> int:
    parser = argparse.ArgumentParser()
    widgets.parser(parser.add_subparsers(dest="command"))
    return widgets.run(parser.parse_args(["widgets", *argv]))


@pytest.mark.parametrize("folder", BUNDLED, ids=[p.name for p in BUNDLED])
def test_every_bundled_widget_passes_the_widget_checks(folder: Path) -> None:
    meta = json.loads((folder / "widget.json").read_text())
    assert library.check_meta(folder.name, meta) == []
    assert lint_widget((folder / "widget.js").read_text()) == []
    assert lint_style((folder / "widget.css").read_text()) == []
    assert all(
        line.startswith(f".w-{folder.name} ") or line[:1] in " @}" or not line.strip()
        for line in (folder / "widget.css").read_text().splitlines()
    )


def test_list_shows_the_bundled_drills(capsys: pytest.CaptureFixture[str]) -> None:
    assert _run("list") == 0
    names = [line.split(" ")[0] for line in capsys.readouterr().out.splitlines()]
    assert names == ["flash-drill", "match-drill", "order-drill", "sort-drill"]


def test_add_copies_the_widget_and_prints_its_block(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = tmp_path / "run"
    assert _run("add", "sort-drill", str(run)) == 0
    assert (run / "widgets" / "sort-drill.js").read_text().startswith("// Sort each card")
    assert (run / "widgets" / "sort-drill.css").is_file()
    out = capsys.readouterr().out
    block = json.loads(out[out.index("{") :])
    assert block["script"] == "widgets/sort-drill.js" and block["data"]["buckets"][0] == "Marsh"
    assert _run("add", "sort-drill", str(run)) == 1
    assert "pass --force" in capsys.readouterr().err
    assert _run("add", "nope", str(run)) == 1


def test_a_repository_widget_hides_the_bundled_one(_home: Path, tmp_path: Path) -> None:
    own = _home / ".chronicle" / "widgets" / "order-drill"
    own.mkdir(parents=True)
    (own / "widget.js").write_text("// our own order drill\nkit.html('p', null, 'x', root);\n")
    (own / "widget.json").write_text(
        json.dumps({"title": "T", "summary": "S", "data": {}, "fallback": "F"})
    )
    assert _run("add", "order-drill", str(tmp_path / "run")) == 0
    assert (tmp_path / "run" / "widgets" / "order-drill.js").read_text().startswith("// our own")


def test_save_keeps_a_runs_widget_and_refuses_unsafe_scripts(
    _home: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    run = tmp_path / "run"
    (run / "widgets").mkdir(parents=True)
    (run / "widgets" / "tide-drill.js").write_text("kit.html('p', null, data.word, root);\n")
    block = {
        "type": "widget",
        "name": "tide-drill",
        "title": "Tides",
        "subtitle": "Guess the tide.",
        "script": "widgets/tide-drill.js",
        "data": {"word": "ebb"},
        "fallback": "Ebb.",
    }
    (run / "story.json").write_text(json.dumps({"chapters": [{"blocks": [block]}]}))
    assert _run("save", str(run), "tide-drill") == 0
    saved = _home / ".chronicle" / "widgets" / "tide-drill"
    assert json.loads((saved / "widget.json").read_text())["summary"] == "Guess the tide."
    (run / "widgets" / "bad-drill.js").write_text("root.innerHTML = data.html;\n")
    block = {**block, "name": "bad-drill"}
    (run / "story.json").write_text(json.dumps({"chapters": [{"blocks": [block]}]}))
    assert _run("save", str(run), "bad-drill", "--to", "config") == 1
    assert "uses innerHTML" in capsys.readouterr().err
