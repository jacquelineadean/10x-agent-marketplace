"""Facts files that join by top-level key, and the locator a fact shows on hover."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from chronicle_engine.core.story.facts import FactError, lookup, merge
from engine_helpers import run, write_story


def test_one_file_is_read_as_it_is() -> None:
    raw = {"a": {"value": 1}, "derive": {"a.b": {"fn": "last", "of": "a.s"}}, "z": 2}
    assert merge([("facts.json", raw)]) == raw
    assert list(merge([("facts.json", raw)])) == ["a", "derive", "z"]


def test_files_join_by_key_and_their_derive_tables_join() -> None:
    joined = merge(
        [
            ("facts.json", {"github": {"x": 1}, "derive": {"github.y": {"fn": "last"}}}),
            ("research/facts.json", {"research": {"z": 2}, "derive": {"research.w": {}}}),
        ]
    )
    assert list(joined) == ["github", "research", "derive"]
    assert list(joined["derive"]) == ["github.y", "research.w"]


def test_a_key_in_two_files_names_both() -> None:
    with pytest.raises(FactError, match="'github' is in both facts.json and notes.json"):
        merge([("facts.json", {"github": {}}), ("notes.json", {"github": {}})])


def test_a_record_keeps_its_locator() -> None:
    facts = {"research": {"founded": {"value": 1886, "source": "book", "locator": "p. 14"}}}
    assert lookup(facts, "research.founded").locator == "p. 14"


def test_a_page_joins_files_and_shows_locators(tmp_path: Path) -> None:
    path = write_story(tmp_path, facts_file=["facts.json", "research/facts.json"])
    story = json.loads(path.read_text(encoding="utf-8"))
    story["chapters"][0]["blocks"][0]["text"] += " Founded {{research.founded}}."
    path.write_text(json.dumps(story), encoding="utf-8")
    (tmp_path / "research").mkdir()
    research = {"research": {"founded": {"value": 1886, "source": "test", "locator": "p. 14"}}}
    (tmp_path / "research" / "facts.json").write_text(json.dumps(research), encoding="utf-8")
    result = run("build", str(path), "--out", str(tmp_path / "build"))
    assert result.returncode == 0, result.stderr
    page = (tmp_path / "build" / "index.html").read_text(encoding="utf-8")
    assert 'data-loc="p. 14"' in page and "4 people" in page


def test_facts_file_must_name_files(tmp_path: Path) -> None:
    path = write_story(tmp_path, facts_file=[])
    result = run("check", str(path))
    assert result.returncode == 1
    assert "facts_file must name a file or a list of files" in result.stderr
