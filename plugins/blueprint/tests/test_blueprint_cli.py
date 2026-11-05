"""blueprint's command line in its own process: every example builds and plays."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
from blueprint_helpers import EXAMPLES, run


@pytest.mark.parametrize("name", ["animation-tad", "checkout-sequence", "orders-erd"])
def test_each_animation_checks_clean_and_builds(name: str, tmp_path: Path) -> None:
    anim = EXAMPLES / name / "animation.json"
    checked = run("animate", "check", str(anim))
    assert checked.returncode == 0 and "0 warning(s)" in checked.stdout, checked.stderr
    built = run("animate", "build", str(anim), "--out", str(tmp_path), "--formats", "svg")
    assert built.returncode == 0, built.stderr
    svg = (tmp_path / "animation.svg").read_text(encoding="utf-8")
    assert svg.startswith("<svg") and 'data-steps="' in svg


def _copy(name: str, tmp: Path) -> Path:
    folder = tmp / name
    shutil.copytree(EXAMPLES / name, folder, symlinks=False)
    return folder / "story.json"


def test_the_architecture_page_wires_parts_pins_and_the_player(tmp_path: Path) -> None:
    story = _copy("checkout-architecture", tmp_path)
    made = run(
        "animate",
        "build",
        str(story.parent / "tad" / "animation.json"),
        "--out",
        str(story.parent / "build" / "tad"),
        "--formats",
        "svg",
    )
    assert made.returncode == 0, made.stderr
    result = run("build", str(story))
    assert result.returncode == 0, result.stderr
    page = (story.parent / "build" / "index.html").read_text(encoding="utf-8")
    assert 'class="fig arch wide"' in page and "INIT.architecture" in page
    assert '"pins":[{"part":"payments"' in page
    assert 'class="mark mark-step"' in page


def test_a_part_the_animation_lacks_is_an_error(tmp_path: Path) -> None:
    story = _copy("checkout-architecture", tmp_path)
    run(
        "animate",
        "build",
        str(story.parent / "tad" / "animation.json"),
        "--out",
        str(story.parent / "build" / "tad"),
        "--formats",
        "svg",
    )
    data = json.loads(story.read_text(encoding="utf-8"))
    data["chapters"][0]["blocks"][0]["pins"].append({"part": "mainframe", "title": "x"})
    story.write_text(json.dumps(data), encoding="utf-8")
    result = run("check", str(story))
    assert result.returncode == 1
    assert "pins[2].part 'mainframe' is not a part" in result.stderr


def test_the_prototype_links_screens(tmp_path: Path) -> None:
    story = _copy("oncall-prototype", tmp_path)
    result = run("build", str(story))
    assert result.returncode == 0, result.stderr
    page = (story.parent / "build" / "index.html").read_text(encoding="utf-8")
    assert page.count('role="tabpanel"') == 4 and page.count("hidden>") >= 3
    assert 'data-link="incidents"' in page and "INIT.cards" in page
    data = json.loads(story.read_text(encoding="utf-8"))
    data["chapters"][0]["blocks"][0]["items"][0]["link"] = "nowhere"
    story.write_text(json.dumps(data), encoding="utf-8")
    broken = run("check", str(story))
    assert broken.returncode == 1 and "link 'nowhere' names no screen" in broken.stderr


def test_schema_prints_an_erd_object() -> None:
    result = run("schema", str(EXAMPLES / "orders-erd" / "schema.csv"))
    assert result.returncode == 0, result.stderr
    assert [e["id"] for e in json.loads(result.stdout)["entities"]][:2] == ["customers", "orders"]


def test_blueprint_starts_tads_and_offers_the_prototype_layout(tmp_path: Path) -> None:
    made = run("animate", "new", str(tmp_path / "a"))
    assert made.returncode == 0, made.stderr
    assert (
        json.loads((tmp_path / "a" / "animation.json").read_text(encoding="utf-8"))["kind"] == "tad"
    )
    new = run("new", str(tmp_path / "p"), "--layout", "prototype")
    assert new.returncode == 0, new.stderr
    assert run("build", str(tmp_path / "p" / "story.json")).returncode == 0
