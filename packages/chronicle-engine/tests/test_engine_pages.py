"""Pages the engine builds alone: the parts each block brings, and the neutral chrome."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from engine_helpers import DIAGRAM_SVG, ENGINE, build, run, write_story

ALWAYS = {
    "css/00-base.css",
    "css/10-page.css",
    "css/12-page.css",
    "css/14-page.css",
    "css/20-identity.css",
    "js/00-core.js",
    "js/40-progress.js",
    "js/90-boot.js",
}
CHART = {
    "type": "chart",
    "chart": "slope",
    "data": {
        "labels": ["Then", "Now"],
        "items": [{"name": "Deploys", "before": 2, "after": 9, "better": "up"}],
    },
}
STATS = {"type": "stats", "items": [{"label": "People", "value": "{{team.size}}"}]}
QUIZ = {"type": "quiz", "questions": [{"q": "How many?", "options": ["3", "4"], "answer": 1}]}
DIAGRAM = {"type": "diagram", "svg": DIAGRAM_SVG, "alt": "Diagram: one box."}
CHARTS = {"js/10-charts.js"}
EXPLAINERS = {"js/50-explainers.js", "css/30-explainers.css"}


def _shipped(page: str) -> set[str]:
    """The engine parts whose text the page carries."""
    parts = [*(ENGINE / "assets" / "css").glob("*.css"), *(ENGINE / "assets" / "js").glob("*.js")]
    return {
        f"{path.parent.name}/{path.name}"
        for path in parts
        if path.read_text(encoding="utf-8") in page
    }


@pytest.mark.parametrize(
    ("blocks", "adds"),
    [
        ([], set()),
        ([CHART], CHARTS),
        ([STATS], CHARTS | {"js/20-figures.js"}),
        ([QUIZ], CHARTS | {"js/60-lessons.js", "css/30-explainers.css"}),
        ([DIAGRAM], EXPLAINERS | {"css/40-drawn.css"}),
        ([CHART, DIAGRAM], CHARTS | EXPLAINERS | {"css/40-drawn.css"}),
    ],
    ids=["prose", "chart", "stats", "quiz", "diagram", "chart-and-diagram"],
)
def test_parts_follow_blocks(tmp_path: Path, blocks: list[dict[str, Any]], adds: set[str]) -> None:
    page = build(tmp_path, blocks or None)
    assert _shipped(page) == ALWAYS | adds


def test_a_page_starts_figures_through_the_starter_table(tmp_path: Path) -> None:
    page = build(tmp_path, [CHART])
    assert "var start = INIT[spec.type];" in page
    assert "INIT.chart = " in page
    assert "INIT.quiz = " not in page


def test_engine_chrome_is_neutral(tmp_path: Path) -> None:
    page = build(tmp_path, [STATS])
    assert '"progress":{"kind":"steps"' in page
    assert 'class="mark mark-label"' in page
    assert "stats-wrap wide stats-rule" in page
    for creative in (".mark-arch", ".pb-arch", ".stats-receipt", ".plate"):
        assert creative not in page, creative


@pytest.mark.parametrize(
    ("theme", "message"),
    [
        ({"progress": {"kind": "arches"}}, "theme.progress.kind 'arches' must be one of steps"),
        ({"progress": {"line": "belt"}}, "theme.progress.line 'belt' must be one of solid, dashed"),
        (
            {"chapter_mark": {"style": "arch"}},
            "theme.chapter_mark.style 'arch' must be one of label, plain, step, none",
        ),
        ({"stats": "receipt"}, "theme.stats 'receipt' must be one of rule, cards"),
        ({"surface": {"frame": "mat"}}, "theme.surface.frame 'mat' must be one of none"),
    ],
)
def test_engine_refuses_creative_chrome(
    tmp_path: Path, theme: dict[str, Any], message: str
) -> None:
    path = write_story(tmp_path, theme={"concept": "A plain test page.", **theme})
    result = run("check", str(path))
    assert result.returncode == 1
    assert message in result.stderr
