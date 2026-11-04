"""Transcript builders for tokenwise tests. Lines follow the shape Claude Code writes."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from tokenwise.core.model import Session
from tokenwise.core.transcript import parse_session

FIXTURES = Path(__file__).parent / "fixtures"
PROJECT = "/work/app"


@dataclass
class Builder:
    """Appends user prompts, assistant responses and tool calls with results."""

    model: str = "claude-sonnet-5-5"
    effort: str = "medium"
    context: int = 20_000
    lines: list[dict[str, Any]] = field(default_factory=list)
    count: int = 0

    def prompt(self, text: str) -> Builder:
        self.lines.append(_user(text))
        return self

    def respond(self, output: int = 100, context: int | None = None, **usage: int) -> Builder:
        self.count += 1
        self.lines.append(self._assistant([{"type": "text", "text": "ok"}], output, context, usage))
        return self

    def tool(
        self, name: str, result: str = "done", is_error: bool = False, **tool_input: Any
    ) -> Builder:
        self.count += 1
        call_id = f"toolu_{self.count}"
        block = {"type": "tool_use", "id": call_id, "name": name, "input": tool_input}
        self.lines.append(self._assistant([block], 50, None, {}))
        content = {"type": "tool_result", "tool_use_id": call_id, "content": result}
        content["is_error"] = is_error
        self.lines.append(_user([content]))
        return self

    def session(self, session_id: str = "s1", agent_type: str = "") -> Session:
        return parse_session(self.lines, session_id, agent_type)

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(line) + "\n" for line in self.lines), encoding="utf-8")
        return path

    def _assistant(
        self, content: list[dict[str, Any]], output: int, context: int | None, usage: dict[str, int]
    ) -> dict[str, Any]:
        total = self.context if context is None else context
        raw = {
            "input_tokens": usage.get("input_tokens", 2),
            "cache_creation_input_tokens": usage.get("cache_write", 0),
            "cache_read_input_tokens": usage.get("cache_read", total - 2),
            "output_tokens": output,
        }
        return {
            "type": "assistant",
            "effort": self.effort,
            "cwd": PROJECT,
            "gitBranch": "main",
            "timestamp": f"2026-11-01T10:{self.count % 60:02d}:00Z",
            "message": {
                "id": f"msg_{self.count}",
                "model": self.model,
                "role": "assistant",
                "content": content,
                "usage": raw,
            },
        }


def _user(content: Any) -> dict[str, Any]:
    return {
        "type": "user",
        "cwd": PROJECT,
        "timestamp": "2026-11-01T10:00:00Z",
        "message": {"role": "user", "content": content},
    }
