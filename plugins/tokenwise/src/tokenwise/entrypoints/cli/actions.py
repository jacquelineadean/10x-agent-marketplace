"""Audit, apply and undo, shared by the commands and the hooks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tokenwise.connectors.files.store import (
    LOCAL_SETTINGS,
    DataFolder,
    Transcript,
    load_session,
    read_json,
    read_workspace,
    write_json,
    write_text,
)
from tokenwise.core.fixes import applied_ids, apply_fixes, undo_changes
from tokenwise.core.handoff import render_handoff
from tokenwise.core.model import Finding, Session
from tokenwise.core.project_rules import find_all
from tokenwise.core.usage import session_usage


@dataclass(frozen=True)
class Audit:
    sessions: list[Session]
    usages: dict[str, dict[str, Any]]
    findings: list[Finding]


def run_audit(transcripts: list[Transcript], project_dir: Path, claude_dir: Path) -> Audit:
    sessions = [load_session(t) for t in transcripts]
    usages = {s.id: session_usage(s) for s in sessions}
    workspace = read_workspace(project_dir, claude_dir)
    return Audit(sessions, usages, find_all(sessions, usages, workspace))


def apply_low_risk(
    project_dir: Path, data: DataFolder, findings: list[Finding], now: str
) -> list[dict[str, Any]]:
    """Write fixes not applied before; an undone fix stays in the ledger and is not reapplied."""
    ledger: list[dict[str, Any]] = read_json(data.ledger, [])
    done = applied_ids(ledger)
    target = project_dir / LOCAL_SETTINGS
    settings, changes = apply_fixes(
        read_json(target, {}), [f for f in findings if f.id not in done]
    )
    if changes:
        write_json(target, settings)
        ledger.append({"at": now, "settings": str(target), "changes": changes})
        write_json(data.ledger, ledger)
    return changes


def undo_last(project_dir: Path, data: DataFolder, now: str) -> list[dict[str, Any]]:
    ledger: list[dict[str, Any]] = read_json(data.ledger, [])
    live = [b for b in ledger if not b.get("undone")]
    if not live:
        return []
    batch = live[-1]
    target = project_dir / LOCAL_SETTINGS
    write_json(target, undo_changes(read_json(target, {}), batch["changes"]))
    batch["undone"] = now
    write_json(data.ledger, ledger)
    changes: list[dict[str, Any]] = batch["changes"]
    return changes


def describe(change: dict[str, Any]) -> str:
    if change["kind"] == "deny":
        return f"deny {change['rule']}"
    return f"env {change['name']}={change['value']}"


def write_handoff(transcript: Path, data: DataFolder, now: datetime) -> Path:
    session = load_session(Transcript(transcript, transcript.stem))
    target = data.handoff(session.id, now.strftime("%Y%m%d-%H%M%S"))
    text = render_handoff(session, session_usage(session), now.isoformat(timespec="seconds"))
    write_text(target, text)
    return target
