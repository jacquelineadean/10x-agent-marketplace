"""Plate notes: pen marks drawn over a painting, checked against the drawing's anchors."""

from __future__ import annotations

import copy
from typing import Any

import pytest
from chronicle.core.story import checks, plates
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Assets, render

MANIFEST = {
    "hero": {
        "file": "art/hero.webp",
        "width": 1800,
        "height": 820,
        "anchors": {"hook": [1200, 204], "load": [1200, 304]},
        "layers": [],
    }
}

NOTES = [
    {"at": "hook", "mark": "circle", "text": "the crane hook"},
    {"at": [900, 400], "mark": "arrow", "text": "load path", "dx": -160, "pen": "blue"},
    {"at": "load", "mark": "underline"},
]


def _with_plate(story: dict[str, Any], notes: list[dict[str, Any]]) -> dict[str, Any]:
    changed = copy.deepcopy(story)
    block = {"type": "plate", "art": "hero", "caption": "Notes", "notes": notes}
    changed["chapters"][0]["blocks"].insert(0, block)
    return changed


@pytest.mark.parametrize("mark", plates.MARKS)
def test_every_mark_is_a_path_that_repeats_for_the_same_seed(mark: str) -> None:
    first = plates.mark_path(mark, 400, 300, 50, 3, (520, 200))
    assert first.startswith("M") and first == plates.mark_path(mark, 400, 300, 50, 3, (520, 200))
    assert first != plates.mark_path(mark, 400, 300, 50, 4, (520, 200)) or mark == "tick"


def test_notes_draw_in_the_overlay_with_staggered_delays(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(_with_plate(story, NOTES), facts, MANIFEST, assets).fragment
    assert page.count('class="pen"') == 3
    assert page.count('class="pen-text"') == 2
    assert 'pathLength="1" stroke="#B8322A"' in page and 'stroke="#2E58A6"' in page
    assert "--d:0.45s" in page and "--d:0.90s" in page
    assert ">the crane hook</text>" in page
    assert 'text-anchor="end"' in page  # the blue note sits to the left of its point


def test_a_plate_without_notes_draws_no_pen_and_ships_no_pen_parts(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(_with_plate(story, []), facts, MANIFEST, assets).fragment
    assert 'class="pen"' not in page
    assert "js/31-notes.js" not in page and "css/16-notes.css" not in page
    noted = render(_with_plate(story, NOTES), facts, MANIFEST, assets).fragment
    assert 'class="notes" data-fig="' in noted
    assert "js/31-notes.js" in noted and "css/16-notes.css" in noted


def test_the_check_names_missing_anchors_and_bad_marks(story: dict[str, Any]) -> None:
    bad = [
        {"at": "nowhere", "mark": "circle"},
        {"at": [1, "2"], "mark": "zigzag", "pen": "green"},
        {"at": "hook", "text": "x" * 70},
        "not a note",
    ]
    report = Report()
    checks.notes(_with_plate(story, bad), {"hero": {"hook", "load"}}, report)
    assert report.errors == [
        "chapters[0].blocks[0].notes[0].at 'nowhere' is no data-anchor in the drawing",
        "chapters[0].blocks[0].notes[1].at must name an anchor or be [x, y] in painting pixels",
        "chapters[0].blocks[0].notes[1].mark must be one of "
        "circle, underline, arrow, cross, tick, box",
        "chapters[0].blocks[0].notes[1].pen must be one of red, blue, ink",
        "chapters[0].blocks[0].notes[3] must be an object",
    ]
    assert report.warnings == ["chapters[0].blocks[0].notes[2].text runs past 60 characters"]
    clean = Report()
    checks.notes(_with_plate(story, NOTES), {}, clean)
    assert clean.errors == [] and clean.warnings == []
