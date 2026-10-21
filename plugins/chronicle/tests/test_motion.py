"""The animation clock, the shared checks, the stage and the HTML around an animation."""

from __future__ import annotations

import re
from typing import Any

import pytest
from chronicle.core.motion import embed, model
from chronicle.core.motion.timeline import Timeline, changes, held, redraws

ANIM: dict[str, Any] = {
    "kind": "diagram",
    "meta": {"title": "Ship it", "description": "A change goes out."},
    "diagram": {"svg": "drawing.svg"},
    "steps": [{"caption": "One."}, {"caption": "Two, a longer caption to read.", "duration": 4}],
}


def test_a_track_runs_the_whole_loop_and_rests_at_its_final_value() -> None:
    clock = Timeline(10.0, loop=True)
    clock.add("#box", "opacity", changes(0.0, [(2.0, 1.0)]), rest=1.0)
    css = clock.css("t")
    assert "animation: t-k0 10.000s linear infinite both" in css
    # No opacity in the rule: the rest value is the default, so a still copy shows it.
    assert re.search(r"#box \{ animation", css)
    assert " 0% { opacity: 0.000; }" in css
    # A loop eases back to its first value before it starts again.
    assert "100% { opacity: 0.000; }" in css


def test_tracks_that_move_the_same_way_share_one_keyframes_block() -> None:
    clock = Timeline(6.0, loop=False)
    for selector in ("#a", "#b"):
        clock.add(selector, "opacity", changes(0.0, [(1.0, 1.0)]))
    css = clock.css("t")
    assert css.count("@keyframes") == 1
    assert "linear 1 both" in css


def test_a_track_that_never_moves_writes_only_its_rest_value() -> None:
    clock = Timeline(5.0, loop=True)
    clock.add("#dim", "opacity", [(0.0, 0.4), (5.0, 0.4)])
    assert clock.css("t") == "#dim { opacity: 0.400; }\n"


def test_only_properties_that_play_in_an_svg_image_can_move() -> None:
    with pytest.raises(ValueError, match="cannot be animated"):
        Timeline(5.0, loop=True).add("#a", "width", [(0.0, 1.0)])


def test_a_redraw_strokes_the_line_on_at_each_start() -> None:
    points = redraws(100.0, [1.0, 5.0], 0.5, drawn=False)
    assert points[0] == (0.0, 100.0)
    assert (1.5, 0.0) in points and (5.5, 0.0) in points
    assert held([(0.0, 1.0), (2.0, 1.0), (3.0, 0.0)])[-1] == (3.0, 0.0)


def test_steps_get_reading_time_and_a_floor() -> None:
    plan = model.plan(ANIM, {}, lambda raw: 3.0)
    first, second = plan.steps
    assert first.start == pytest.approx(0.6)
    assert first.duration >= 3.0  # the floor beats the reading time of a short caption
    assert second.duration == 4.0  # a duration given in the step wins
    assert plan.duration == pytest.approx(second.end + 2.0)  # the last step holds 2 s


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"kind": "movie"}, "kind must be one of"),
        ({"meta": {"title": "X"}}, "meta.description is required"),
        ({"steps": [{"state": {"a": "down"}}]}, "state does not apply to a diagram"),
        ({"steps": [{"show": "box"}]}, "show must be a list of ids"),
        ({"frame": {"size": "2:1"}}, "frame.size must be one of"),
        ({"steps": [{"caption": "Up 40% this year."}]}, "has no fact token"),
    ],
)
def test_shared_checks_name_the_problem(change: dict[str, Any], message: str) -> None:
    report = model.check({**ANIM, **change}, {})
    assert any(message in m for m in report.errors + report.warnings), report


def test_the_figure_pastes_without_scripts_and_lists_the_steps() -> None:
    plan = model.plan(ANIM, {}, lambda raw: 0.0)
    fragment = embed.figure(plan, '<svg class="chr-a"></svg>')
    assert "<script" not in fragment
    assert 'type="checkbox"' in fragment and "animation-play-state: paused" in fragment
    assert "<li>Two, a longer caption to read.</li>" in fragment
    assert embed.page(plan, fragment).startswith("<!doctype html>")
    assert "--seek" in embed.capture("<svg></svg>")
