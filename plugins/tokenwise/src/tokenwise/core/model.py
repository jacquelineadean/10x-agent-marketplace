"""Domain records read from one Claude Code transcript."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

TIERS = ("low", "medium", "high")
EDIT_TOOLS_NAMES = frozenset({"Edit", "Write", "NotebookEdit", "MultiEdit"})


@dataclass(frozen=True)
class Usage:
    """Token counts from one API response, deduplicated by message id."""

    input_tokens: int = 0
    cache_write_5m: int = 0
    cache_write_1h: int = 0
    cache_read: int = 0
    output_tokens: int = 0

    @property
    def context(self) -> int:
        """Tokens the model read for this response: the context size at that turn."""
        return self.input_tokens + self.cache_write_5m + self.cache_write_1h + self.cache_read


@dataclass(frozen=True)
class Response:
    id: str
    model: str
    effort: str
    usage: Usage


@dataclass
class ToolCall:
    id: str
    name: str
    input: dict[str, Any]
    result_chars: int = 0
    is_error: bool = False
    answered: bool = False

    @property
    def command(self) -> str:
        """Bash command with whitespace collapsed, or empty for other tools."""
        raw = self.input.get("command")
        return " ".join(raw.split()) if isinstance(raw, str) else ""

    @property
    def path(self) -> str:
        raw = self.input.get("file_path") or self.input.get("notebook_path")
        return raw if isinstance(raw, str) else ""


@dataclass
class Session:
    id: str
    cwd: str = ""
    branch: str = ""
    started: str = ""
    ended: str = ""
    agent_type: str = ""
    responses: list[Response] = field(default_factory=list)
    tools: list[ToolCall] = field(default_factory=list)
    prompts: list[str] = field(default_factory=list)

    @property
    def is_subagent(self) -> bool:
        return bool(self.agent_type)


@dataclass(frozen=True)
class Finding:
    """One optimization opportunity. `fix` is set only when code can apply it safely."""

    rule: str
    key: str
    tier: str
    title: str
    evidence: str
    advice: str
    at_stake: int
    sessions: tuple[str, ...] = ()
    fix: dict[str, str] | None = None

    @property
    def id(self) -> str:
        return f"{self.rule}:{self.key}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "rule": self.rule,
            "tier": self.tier,
            "title": self.title,
            "evidence": self.evidence,
            "advice": self.advice,
            "at_stake_tokens": self.at_stake,
            "sessions": list(self.sessions),
            "fix": self.fix,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> Finding:
        return cls(
            rule=raw["rule"],
            key=raw["id"].split(":", 1)[1],
            tier=raw["tier"],
            title=raw["title"],
            evidence=raw["evidence"],
            advice=raw["advice"],
            at_stake=raw["at_stake_tokens"],
            sessions=tuple(raw["sessions"]),
            fix=raw["fix"],
        )


@dataclass(frozen=True)
class Workspace:
    """Project facts read from disk: instruction files that load every turn, MCP servers."""

    project_dir: str
    instruction_files: dict[str, int] = field(default_factory=dict)
    mcp_servers: tuple[str, ...] = ()
