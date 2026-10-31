"""The source picker: the questions a skill asks when the request names no system."""

from __future__ import annotations

from typing import Any

from sources.core.detect import Status
from sources.core.systems import GROUPS


def questions(statuses: list[Status]) -> list[dict[str, Any]]:
    """One multi-select question per group, one option per system with its status.

    The output is the `questions` argument of AskUserQuestion as is.
    """
    out = []
    for group, (header, question) in GROUPS.items():
        options = [
            {"label": s.system.label, "description": s.text}
            for s in statuses
            if s.system.group == group
        ]
        out.append(
            {"question": question, "header": header, "multiSelect": True, "options": options}
        )
    return out
