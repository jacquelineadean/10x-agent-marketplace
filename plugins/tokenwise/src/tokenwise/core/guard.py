"""Loop guard: count failures of the same Bash command within one session.

At the third failure Claude gets one reminder to change approach. A success resets the count.
"""

from __future__ import annotations

from typing import Any

WARN_AT = 3


def record(state: dict[str, Any], command: str, failed: bool) -> tuple[dict[str, Any], str]:
    """Return the new state and a reminder, empty unless this failure reaches WARN_AT."""
    key = " ".join(command.split())
    counts = dict(state.get("failures", {}))
    if not failed:
        counts.pop(key, None)
        return {**state, "failures": counts}, ""
    counts[key] = counts.get(key, 0) + 1
    message = ""
    if counts[key] == WARN_AT:
        message = (
            f"tokenwise: this command failed {WARN_AT} times in a row. Stop retrying it. "
            "Read the error, check the cause (missing tool, path, setup step), then change "
            "the approach or ask the user."
        )
    return {**state, "failures": counts}, message
