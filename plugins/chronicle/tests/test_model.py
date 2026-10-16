from __future__ import annotations

import copy
from typing import Any

from chronicle.core.story import model


def test_keystone_example_is_clean(story: dict[str, Any], facts: dict[str, Any]) -> None:
    report = model.check(story, facts)
    assert report.errors == []
    assert report.warnings == []


def test_unknown_block_type_lists_the_choices(story: dict[str, Any], facts: dict[str, Any]) -> None:
    broken = copy.deepcopy(story)
    broken["chapters"][0]["blocks"].append({"type": "carousel"})
    errors = model.check(broken, facts).errors
    assert any("'carousel' is unknown" in e and "prose" in e for e in errors)


def test_missing_fact_is_an_error(story: dict[str, Any], facts: dict[str, Any]) -> None:
    broken = copy.deepcopy(story)
    broken["chapters"][0]["blocks"].append({"type": "prose", "text": "We hit {{nope.value}}."})
    errors = model.check(broken, facts).errors
    assert any("no fact 'nope.value'" in e for e in errors)


def test_typed_number_is_a_warning(story: dict[str, Any], facts: dict[str, Any]) -> None:
    changed = copy.deepcopy(story)
    changed["chapters"][0]["blocks"].append({"type": "prose", "text": "Latency fell 64%."})
    report = model.check(changed, facts)
    assert report.ok
    assert any("'64%' has no fact token" in w for w in report.warnings)


def test_typed_number_in_a_quiz_question_is_a_warning(
    story: dict[str, Any], facts: dict[str, Any]
) -> None:
    changed = copy.deepcopy(story)
    question = {"q": "A shot runs 18 seconds. Why?", "options": ["Fast", "Slow"], "answer": 0}
    changed["chapters"][0]["blocks"].append({"type": "quiz", "questions": [question]})
    report = model.check(changed, facts)
    assert any("questions[0].q: number '18'" in w for w in report.warnings)


def test_structure_errors(story: dict[str, Any], facts: dict[str, Any]) -> None:
    broken = copy.deepcopy(story)
    broken["chapters"][1]["id"] = broken["chapters"][0]["id"]
    broken["chapters"][2]["art"] = "missing-scene"
    broken["chapters"][3]["blocks"].append({"type": "chart", "data": {}})
    errors = model.check(broken, facts).errors
    assert any("is used twice" in e for e in errors)
    assert any("'missing-scene' is not defined in art" in e for e in errors)
    assert any("is missing 'chart'" in e for e in errors)
