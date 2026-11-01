"""briefing's command line in its own process: the keystone deck and dashboard, new runs,
brand kits and exports."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from briefing_helpers import EXAMPLES, PLUGIN, run

ENGINE_ASSETS = PLUGIN / "src" / "chronicle_engine" / "assets"
OWN_ASSETS = PLUGIN / "src" / "briefing" / "assets"


def _copy(name: str, tmp: Path) -> Path:
    """An example in a temporary folder, its links resolved, so builds write nowhere else."""
    folder = tmp / name
    shutil.copytree(EXAMPLES / name, folder, symlinks=False)
    return folder / "story.json"


@pytest.fixture(scope="module")
def dashboard(tmp_path_factory: pytest.TempPathFactory) -> str:
    story = _copy("keystone-dashboard", tmp_path_factory.mktemp("dash"))
    result = run("build", str(story))
    assert result.returncode == 0, result.stderr
    return (story.parent / "build" / "index.html").read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def deck(tmp_path_factory: pytest.TempPathFactory) -> str:
    story = _copy("keystone-deck", tmp_path_factory.mktemp("deck"))
    made = run(
        "animate",
        "build",
        str(story.parent / "anim" / "animation.json"),
        "--out",
        str(story.parent / "build" / "anim"),
        "--formats",
        "svg",
    )
    assert made.returncode == 0, made.stderr
    result = run("build", str(story))
    assert result.returncode == 0, result.stderr
    return (story.parent / "build" / "index.html").read_text(encoding="utf-8")


def test_the_dashboard_sets_each_status_by_rule(dashboard: str) -> None:
    assert dashboard.count('class="stat kpi kpi-good"') == 4
    assert dashboard.count('class="stat kpi kpi-warn"') == 1
    assert dashboard.count('class="stat kpi kpi-bad"') == 1
    assert '<p class="db-asof">As of 14 Oct 2026</p>' in dashboard
    assert 'data-query="p95:trace.http.request.duration' in dashboard


def test_the_dashboard_renders_one_copy_per_filter_option(dashboard: str) -> None:
    assert dashboard.count('class="slice" data-slice="state"') == 4
    assert dashboard.count('data-slice="state" data-option="NV">') == 1
    assert dashboard.count('data-slice="state" data-option="OR" hidden>') == 1


def test_pages_ship_briefing_parts_and_none_of_chronicles(dashboard: str, deck: str) -> None:
    kpi_script = (OWN_ASSETS / "js" / "71-kpi.js").read_text(encoding="utf-8")
    deck_script = (OWN_ASSETS / "js" / "70-deck.js").read_text(encoding="utf-8")
    assert kpi_script in dashboard and kpi_script in deck
    assert deck_script in deck and deck_script not in dashboard
    for creative in ("mark-arch", "pb-route", "stats-receipt", "INIT.plate"):
        assert creative not in dashboard and creative not in deck


def test_the_deck_has_a_cover_a_slide_per_chapter_and_sources(deck: str) -> None:
    assert deck.count('<section class="slide') == 7
    assert 'id="cover"' in deck and 'id="sources-slide"' in deck
    assert 'class="build" data-build' in deck
    assert '<aside class="slide-notes">' in deck
    assert 'data-steps="0.6,5.975,' in deck and 'data-end="' in deck  # steps per click


def test_new_starts_a_deck(tmp_path: Path) -> None:
    folder = tmp_path / "runs" / "q4"
    result = run("new", str(folder), "--layout", "deck", "--title", "Q4 review")
    assert result.returncode == 0, result.stderr
    story = json.loads((folder / "story.json").read_text(encoding="utf-8"))
    assert story["layout"] == "deck"
    assert [c["id"] for c in story["chapters"]] == ["decision", "numbers"]
    assert run("build", str(folder / "story.json")).returncode == 0


def _kit(path: Path, accent: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    kit = {"name": "Acme", "palette": {"accent": accent}, "fonts": {"display": "Fraunces"}}
    path.write_text(json.dumps(kit), encoding="utf-8")


def test_brand_kits_come_from_the_run_repo_config_or_a_path(tmp_path: Path) -> None:
    folder = tmp_path / "repo" / "runs" / "kit"
    (tmp_path / "repo" / ".git").mkdir(parents=True)
    _kit(tmp_path / "repo" / ".brand" / "brand.json", "#0055AA")
    _kit(tmp_path / "config" / "chronicle" / "brand.json", "#AA3300")
    env = {"XDG_CONFIG_HOME": str(tmp_path / "config")}
    assert run("new", str(folder), "--brand", "repo", env=env).returncode == 0
    assert json.loads((folder / "brand.json").read_text(encoding="utf-8"))["name"] == "Acme"
    story = folder / "story.json"
    assert run("build", str(story), env=env).returncode == 0
    page = (folder / "build" / "index.html").read_text(encoding="utf-8")
    assert "--accent: #0055AA;" in page and "Fraunces" in page
    assert run("build", str(story), "--brand", "config", env=env).returncode == 0
    page = (folder / "build" / "index.html").read_text(encoding="utf-8")
    assert "--accent: #AA3300;" in page
    data = json.loads(story.read_text(encoding="utf-8"))
    data["theme"]["palette"] = {"accent": "#123456"}
    story.write_text(json.dumps(data), encoding="utf-8")
    result = run("check", str(story), env=env)
    assert "theme.palette.accent '#123456' departs from Acme's '#0055AA'" in result.stderr
    missing = run("check", str(story), "--brand", str(tmp_path / "none.json"))
    assert missing.returncode == 1 and "no brand kit at" in missing.stderr


def test_exports_hold_formatted_numbers_and_their_queries(tmp_path: Path) -> None:
    story = _copy("keystone-dashboard", tmp_path)
    assert run("export", str(story), "--to", "dashboard").returncode == 0
    data = json.loads((story.parent / "build" / "dashboard.json").read_text(encoding="utf-8"))
    tile = data["sections"][0]["kpis"][0]
    assert tile["value"] == "71%" and tile["target"] == "80%" and tile["status"] == "Off target"
    assert tile["query"].startswith("sum:trace.http.request.hits")
    assert data["as_of"] == "2026-10-14"


def test_the_sources_command_is_linked(tmp_path: Path) -> None:
    result = run(
        "sources", "detect", "--picker", env={"SOURCES_CONNECTIONS": str(tmp_path / "c.json")}
    )
    assert result.returncode == 0, result.stderr
    assert [q["header"] for q in json.loads(result.stdout)] == ["Code & work", "Operations", "Data"]


def test_slides_and_check_report_bad_input_as_errors(tmp_path: Path) -> None:
    story = _copy("keystone-dashboard", tmp_path)
    unbuilt = run("slides", str(story), "--png")
    assert unbuilt.returncode == 1 and "run build first" in unbuilt.stderr
    (story.parent / "queries.json").write_text("[]", encoding="utf-8")
    checked = run("check", str(story))
    assert "Traceback" not in checked.stderr, checked.stderr
