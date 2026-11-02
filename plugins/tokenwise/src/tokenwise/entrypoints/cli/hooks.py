"""Claude Code hooks. Each reads the event JSON from stdin and finishes in well under a second.

Hooks print JSON only when they have something to say. `systemMessage` is shown to the user;
`additionalContext` reaches Claude and costs tokens, so only the loop guard uses it.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from tokenwise.config.settings import Settings
from tokenwise.connectors.files.store import (
    DataFolder,
    Transcript,
    read_json,
    subagent_transcripts,
    write_json,
)
from tokenwise.core.guard import record
from tokenwise.core.model import TIERS
from tokenwise.entrypoints.cli.actions import apply_low_risk, describe, run_audit, write_handoff

EXIT_OK = 0


def run_hook(
    event: str, payload: dict[str, Any], settings: Settings, out: TextIO, now: datetime
) -> int:
    session_id = str(payload.get("session_id") or "")
    project = Path(str(payload.get("cwd") or ".")).resolve()
    data = DataFolder.for_project(settings.runs_root, project)
    if event == "bash-result":
        return _bash_result(payload, data, session_id, out)
    transcript = Path(str(payload.get("transcript_path") or ""))
    if not transcript.is_file():
        return EXIT_OK
    if event == "pre-compact":
        target = write_handoff(transcript, data, now)
        _emit(out, {"systemMessage": f"tokenwise: handoff facts saved to {target}"})
        return EXIT_OK
    return _stop(transcript, project, data, session_id, settings, out, now)


def _bash_result(payload: dict[str, Any], data: DataFolder, session_id: str, out: TextIO) -> int:
    tool_input = payload.get("tool_input") or {}
    command = str(tool_input.get("command") or "") if isinstance(tool_input, dict) else ""
    if not command or payload.get("is_interrupt"):
        return EXIT_OK
    event = str(payload.get("hook_event_name") or "PostToolUse")
    path = data.state(session_id)
    state, message = record(read_json(path, {}), command, failed=event == "PostToolUseFailure")
    write_json(path, state)
    if message:
        _emit(out, {"hookSpecificOutput": {"hookEventName": event, "additionalContext": message}})
    return EXIT_OK


def _stop(
    transcript: Path,
    project: Path,
    data: DataFolder,
    session_id: str,
    settings: Settings,
    out: TextIO,
    now: datetime,
) -> int:
    """Audit this session only; report findings not reported before, apply low-risk fixes."""
    transcripts = [Transcript(transcript, transcript.stem), *subagent_transcripts(transcript)]
    findings = run_audit(transcripts, project, settings.claude_dir).findings
    path = data.state(session_id)
    state = read_json(path, {})
    reported = set(state.get("reported", []))
    fresh = [f for f in findings if f.id not in reported]
    changes = []
    if settings.auto_apply:
        changes = apply_low_risk(project, data, fresh, now.isoformat(timespec="seconds"))
    write_json(path, {**state, "reported": sorted(reported | {f.id for f in findings})})
    if not fresh:
        return EXIT_OK
    counts = Counter(f.tier for f in fresh)
    tiers = ", ".join(f"{counts[t]} {t}" for t in TIERS if counts[t])
    message = (
        f"tokenwise: {len(fresh)} new findings ({tiers}), "
        f"about {sum(f.at_stake for f in fresh):,} tokens at stake. Run /tokenwise:audit."
    )
    if changes:
        applied = "; ".join(describe(c) for c in changes)
        message += f" Applied to .claude/settings.local.json: {applied} (undo: tokenwise undo)."
    _emit(out, {"systemMessage": message})
    return EXIT_OK


def _emit(out: TextIO, value: dict[str, Any]) -> None:
    out.write(json.dumps(value) + "\n")
