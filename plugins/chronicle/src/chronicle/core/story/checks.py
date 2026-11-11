"""chronicle's checks on its own blocks: what a story names must exist and fit.

The anchors come from each drawing's `data-anchor` points, read by the caller; a painting
made from a preset or motifs has none to check against.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from chronicle_engine.core.story.model import Report, blocks_of

from chronicle.core.story.plates import MARKS, PENS

MAX_NOTES = 8
NOTE_CHARS = 60


def _at(at: Any, anchors: set[str] | None, where: str, report: Report) -> None:
    if isinstance(at, str):
        if anchors is not None and at not in anchors:
            report.errors.append(f"{where}.at {at!r} is no data-anchor in the drawing")
    elif not (
        isinstance(at, list | tuple)
        and len(at) == 2
        and all(isinstance(v, int | float) and not isinstance(v, bool) for v in at)
    ):
        report.errors.append(f"{where}.at must name an anchor or be [x, y] in painting pixels")


def notes(story: Mapping[str, Any], anchors: Mapping[str, set[str]], report: Report) -> None:
    """Plate notes: a list of marks at anchors or points, each with short words."""
    for where, block in blocks_of(story, "plate"):
        found = block.get("notes")
        if found is None:
            continue
        if not isinstance(found, list) or len(found) > MAX_NOTES:
            report.errors.append(f"{where}.notes must be a list of at most {MAX_NOTES} notes")
            continue
        for k, note in enumerate(found):
            here = f"{where}.notes[{k}]"
            if not isinstance(note, Mapping):
                report.errors.append(f"{here} must be an object")
                continue
            _at(note.get("at"), anchors.get(str(block.get("art"))), here, report)
            if note.get("mark", "circle") not in MARKS:
                report.errors.append(f"{here}.mark must be one of {', '.join(MARKS)}")
            if note.get("pen", "red") not in PENS:
                report.errors.append(f"{here}.pen must be one of {', '.join(PENS)}")
            if len(str(note.get("text", ""))) > NOTE_CHARS:
                report.warnings.append(f"{here}.text runs past {NOTE_CHARS} characters")
