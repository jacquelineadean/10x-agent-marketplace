"""Every file read and write: transcripts (read-only), project files, the data folder."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from tokenwise.core.model import Session, Workspace
from tokenwise.core.transcript import parse_session

log = logging.getLogger("tokenwise")
INSTRUCTION_FILES = ("CLAUDE.md", "CLAUDE.local.md", ".claude/CLAUDE.md", "AGENTS.md")
LOCAL_SETTINGS = Path(".claude") / "settings.local.json"


@dataclass(frozen=True)
class Transcript:
    path: Path
    session_id: str
    agent_type: str = ""


def project_slug(project_dir: Path) -> str:
    """Claude Code names a project's transcript folder after its path, non-alphanumerics as '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(project_dir))


def find_transcripts(claude_dir: Path, project_dir: Path, since: datetime) -> list[Transcript]:
    folder = claude_dir / "projects" / project_slug(project_dir)
    found: list[Transcript] = []
    for path in sorted(folder.glob("*.jsonl")):
        if datetime.fromtimestamp(path.stat().st_mtime).astimezone() < since:
            continue
        found.append(Transcript(path, path.stem))
        found.extend(subagent_transcripts(path))
    return found


def subagent_transcripts(main: Path) -> list[Transcript]:
    """Subagents write `<session>/subagents/agent-<id>.jsonl` with a `.meta.json` beside it."""
    found = []
    for path in sorted((main.parent / main.stem / "subagents").glob("agent-*.jsonl")):
        meta = path.with_suffix(".meta.json")
        agent_type = "subagent"
        if meta.is_file():
            agent_type = str(read_json(meta, {}).get("agentType") or agent_type)
        found.append(Transcript(path, path.stem, agent_type))
    return found


def load_session(transcript: Transcript) -> Session:
    return parse_session(_lines(transcript.path), transcript.session_id, transcript.agent_type)


def _lines(path: Path) -> Iterator[dict[str, Any]]:
    bad = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                bad += 1  # a line still being written when the hook fires
                continue
            if isinstance(value, dict):
                yield value
    if bad:
        log.warning("skipped %d unreadable lines in %s", bad, path.name)


def read_workspace(project_dir: Path, claude_dir: Path) -> Workspace:
    files = {
        name: (project_dir / name).stat().st_size
        for name in INSTRUCTION_FILES
        if (project_dir / name).is_file()
    }
    user_file = claude_dir / "CLAUDE.md"
    if user_file.is_file():
        files["~/.claude/CLAUDE.md"] = user_file.stat().st_size
    servers = read_json(project_dir / ".mcp.json", {}).get("mcpServers", {})
    return Workspace(
        project_dir=str(project_dir),
        instruction_files=files,
        mcp_servers=tuple(sorted(servers)) if isinstance(servers, dict) else (),
    )


def read_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


@dataclass(frozen=True)
class DataFolder:
    """`~/tokenwise-runs/<project slug>/`: outputs, the apply ledger and hook state."""

    root: Path

    @classmethod
    def for_project(cls, runs_root: Path, project_dir: Path) -> DataFolder:
        return cls(runs_root / project_slug(project_dir).strip("-"))

    @property
    def ledger(self) -> Path:
        return self.root / "applied.json"

    def state(self, session_id: str) -> Path:
        return self.root / "state" / f"{re.sub(r'[^A-Za-z0-9_-]', '', session_id)}.json"

    def handoff(self, session_id: str, stamp: str) -> Path:
        return self.root / "handoffs" / f"{session_id[:8]}-{stamp}.md"
