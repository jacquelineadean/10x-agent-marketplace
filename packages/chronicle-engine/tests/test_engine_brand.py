"""Brand kits, queries shown on hover, and layouts, with the engine alone."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from chronicle_engine.core.story import brand
from chronicle_engine.core.story.facts import attach_queries
from chronicle_engine.core.story.theme import ThemeError
from chronicle_engine.entrypoints.cli import runs
from engine_helpers import build, run, write_story

KIT = {"name": "Acme", "palette": {"accent": "#0055AA", "ink": "#111111"}, "fonts": {"ui": "Inter"}}


def test_a_kit_fills_the_theme_where_it_is_silent() -> None:
    theme = {"concept": "x", "palette": {"accent": "#123456"}}
    merged = brand.apply(theme, KIT)
    assert merged["palette"] == {"accent": "#123456", "ink": "#111111"}
    assert merged["fonts"] == {"ui": "Inter"}
    assert brand.departures(theme, KIT) == [
        "theme.palette.accent '#123456' departs from Acme's '#0055AA'"
    ]


@pytest.mark.parametrize(
    ("kit", "message"),
    [
        ({"logo": "x.svg"}, "field 'logo' is unknown"),
        ({"palette": {"brand": "#000000"}}, "palette.brand is unknown"),
        ({"fonts": {"script": "Caveat"}}, "fonts.script is unknown"),
        ({"schema_version": 2}, "schema_version must be 1"),
    ],
)
def test_a_bad_kit_says_what_to_change(kit: dict[str, object], message: str) -> None:
    with pytest.raises(ThemeError, match=message):
        brand.check_kit(kit)


def test_kits_resolve_from_the_run_repo_config_or_a_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_folder = tmp_path / "repo" / "runs" / "a"
    run_folder.mkdir(parents=True)
    assert runs.brand_kit("run", run_folder) is None
    (tmp_path / "repo" / ".git").mkdir()
    (tmp_path / "repo" / ".brand").mkdir()
    (tmp_path / "repo" / ".brand" / "brand.json").write_text(json.dumps(KIT), encoding="utf-8")
    assert runs.brand_kit("repo", run_folder) == KIT
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    with pytest.raises(OSError, match="no brand kit at .*cfg/chronicle/brand.json"):
        runs.brand_kit("config", run_folder)
    (run_folder / "brand.json").write_text(json.dumps({"name": "Run"}), encoding="utf-8")
    assert runs.brand_kit("run", run_folder) == {"name": "Run"}
    assert runs.brand_kit(str(run_folder / "brand.json"), tmp_path) == {"name": "Run"}


def test_a_group_query_passes_down_and_a_record_keeps_its_own() -> None:
    facts = {
        "github": {"a": {"value": 1}, "b": {"value": 2, "query": "own"}, "s": [1, 2]},
        "derive": {"github.c": {"fn": "last", "of": "github.s"}},
    }
    out = attach_queries(facts, {"github": "group", "github.a": "mine"})
    assert out["github"]["a"]["query"] == "mine"
    assert out["github"]["b"]["query"] == "own"
    assert out["github"]["s"] == [1, 2]
    assert out["derive"] == facts["derive"]


def test_a_page_shows_each_query_on_hover(tmp_path: Path) -> None:
    queries = {"queries": {"team": {"query": "count of people"}}}
    (tmp_path / "queries.json").write_text(json.dumps(queries), encoding="utf-8")
    page = build(tmp_path)
    assert 'data-query="count of people"' in page


def test_the_engine_offers_only_the_page_layout(tmp_path: Path) -> None:
    path = write_story(tmp_path, layout="deck")
    result = run("check", str(path))
    assert result.returncode == 1
    assert "layout 'deck' must be one of page" in result.stderr
    made = run("new", str(tmp_path / "x"), "--layout", "deck")
    assert made.returncode == 2 and "invalid choice" in made.stderr
