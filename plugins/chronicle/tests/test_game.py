"""Game scoring on the Python side: holes from quizzes, next links, the scorecard, the check."""

from __future__ import annotations

import copy
import json
import re
from typing import Any

from chronicle.core.story import game
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Assets, render

QUESTION = {"q": "Which grind?", "options": ["Coarser", "Finer"], "answer": 1, "explain": "Finer."}


def _story(story: dict[str, Any], with_game: bool) -> dict[str, Any]:
    out = copy.deepcopy(story)
    quiz = {"type": "quiz", "title": "First hole", "questions": [QUESTION, QUESTION]}
    out["chapters"][0]["blocks"].append(quiz)
    second = {"type": "quiz", "id": "last", "questions": [QUESTION], "par": 3}
    out["chapters"][1]["blocks"].append(second)
    out["chapters"][-1]["blocks"].append({"type": "scorecard", "title": "Your card"})
    if with_game:
        out["game"] = {"names": {"0": "Even"}, "key": "keystone-round"}
    return out


def _figs(html: str, kind: str) -> list[dict[str, Any]]:
    data = json.loads(re.search(r'id="chronicle-data">(.*?)</script>', html).group(1))  # type: ignore[union-attr]
    return [f for f in data["figs"].values() if f["type"] == kind]


def test_without_a_game_a_quiz_is_the_engines_quiz(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(_story(story, False), facts, {}, assets).fragment
    assert 'class="fig quiz col"' in page and 'class="fig hole col"' not in page


def test_with_a_game_quizzes_become_holes_that_link_onward(
    story: dict[str, Any], facts: dict[str, Any], assets: Assets
) -> None:
    page = render(_story(story, True), facts, {}, assets).fragment
    holes = _figs(page, "hole")
    assert [(h["id"], h["no"], h["par"]) for h in holes] == [("hole-1", 1, 3), ("last", 2, 3)]
    assert holes[0]["next"] == {"href": "#last", "label": "Next hole"}
    assert holes[1]["next"] == {"href": "#scorecard", "label": "See your card"}
    assert holes[0]["names"]["0"] == "Even" and holes[0]["names"]["-1"] == "Birdie"
    assert holes[0]["key"] == "chronicle-game:keystone-round"
    assert '<section class="fig hole col" id="hole-1"' in page
    assert page.count('class="hl-opt"') == 6
    card = _figs(page, "scorecard")[0]
    assert [r["id"] for r in card["holes"]] == ["hole-1", "last"]
    assert "<td>6</td>" in page  # the total par of 3 and 3


def test_the_check_refuses_bad_names_ids_and_pars(story: dict[str, Any]) -> None:
    bad = _story(story, True)
    bad["game"] = {"names": {"under": "Birdie"}}
    bad["chapters"][1]["blocks"][-1]["par"] = 0
    bad["chapters"][1]["blocks"][-1]["id"] = "hole-1"
    report = Report()
    game.check(bad, report)
    assert report.errors == [
        'game.names maps strokes against par ("-1", "0", "1") to words',
        "hole 2: id 'hole-1' must be unique, lowercase letters and -",
        "hole 2: par must be a whole number of at least 1",
    ]
    lonely = Report()
    game.check({"game": {}, "chapters": []}, lonely)
    assert lonely.warnings == ["game is set but the story has no quiz to play as a hole"]
