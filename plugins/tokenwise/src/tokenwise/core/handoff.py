"""Handoff facts for a fresh session: what was asked, what changed, what ran, what failed.

Code writes the facts; the handoff skill adds the state and next steps in Claude's words.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from tokenwise.core.model import EDIT_TOOLS_NAMES, Session

MAX_PROMPT_CHARS = 600
MAX_COMMANDS = 12
MAX_FAILURES = 6


def render_handoff(session: Session, usage: dict[str, Any], written_at: str) -> str:
    prompts = [p.strip() for p in session.prompts if p.strip() and not p.startswith("<")]
    edits = Counter(c.path for c in session.tools if c.name in EDIT_TOOLS_NAMES and c.path)
    commands = list(dict.fromkeys(c.command for c in session.tools if c.command))
    failures = list(dict.fromkeys(c.command for c in session.tools if c.command and c.is_error))
    lines = [
        f"# Handoff: session {session.id}",
        "",
        f"Written {written_at}. Directory `{session.cwd or 'unknown'}`, "
        f"branch `{session.branch or 'unknown'}`. {usage['responses']} responses, "
        f"peak context {usage['peak_context']:,} tokens.",
        "",
        "## First request",
        _quote(prompts[0]) if prompts else "_none recorded_",
    ]
    if len(prompts) > 1:
        lines += ["", "## Latest request", _quote(prompts[-1])]
    lines += ["", "## Files changed"]
    lines += [f"- `{path}` ({count} edits)" for path, count in edits.most_common()] or ["_none_"]
    lines += ["", f"## Commands run (last {MAX_COMMANDS})"]
    lines += [f"- `{c[:160]}`" for c in commands[-MAX_COMMANDS:]] or ["_none_"]
    if failures:
        lines += ["", "## Commands that failed"]
        lines += [f"- `{c[:160]}`" for c in failures[-MAX_FAILURES:]]
    lines += ["", "## State and next steps", "_Written by Claude from the session._", ""]
    return "\n".join(lines)


def _quote(text: str) -> str:
    cut = text if len(text) <= MAX_PROMPT_CHARS else text[:MAX_PROMPT_CHARS] + " [...]"
    return "\n".join(f"> {line}" for line in cut.splitlines())
