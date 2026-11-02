"""Build a Session from transcript lines. Pure: the caller reads the file.

Claude Code writes one line per content block, so a response with thinking, text and two
tool calls appears on four lines with the same `message.id` and the same usage. Usage is
counted once per id.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from tokenwise.core.model import Response, Session, ToolCall, Usage


def parse_session(
    lines: Iterable[dict[str, Any]], session_id: str, agent_type: str = ""
) -> Session:
    session = Session(id=session_id, agent_type=agent_type)
    seen: set[str] = set()
    calls: dict[str, ToolCall] = {}
    for line in lines:
        kind = line.get("type")
        if kind not in ("assistant", "user"):
            continue
        _stamp(session, line)
        message = line.get("message")
        if not isinstance(message, dict):
            continue
        if kind == "assistant":
            _assistant(session, line, message, seen, calls)
        else:
            _user(session, message, calls)
    return session


def _stamp(session: Session, line: dict[str, Any]) -> None:
    stamp = str(line.get("timestamp") or "")
    if stamp:
        session.started = session.started or stamp
        session.ended = stamp
    session.cwd = session.cwd or str(line.get("cwd") or "")
    session.branch = session.branch or str(line.get("gitBranch") or "")


def _assistant(
    session: Session,
    line: dict[str, Any],
    message: dict[str, Any],
    seen: set[str],
    calls: dict[str, ToolCall],
) -> None:
    message_id = str(message.get("id") or "")
    if message_id and message_id not in seen and isinstance(message.get("usage"), dict):
        seen.add(message_id)
        session.responses.append(
            Response(
                id=message_id,
                model=str(message.get("model") or ""),
                effort=str(line.get("effort") or ""),
                usage=_usage(message["usage"]),
            )
        )
    for block in _blocks(message):
        if block.get("type") == "tool_use":
            raw_input = block.get("input")
            call = ToolCall(
                id=str(block.get("id") or ""),
                name=str(block.get("name") or ""),
                input=raw_input if isinstance(raw_input, dict) else {},
            )
            calls[call.id] = call
            session.tools.append(call)


def _user(session: Session, message: dict[str, Any], calls: dict[str, ToolCall]) -> None:
    content = message.get("content")
    if isinstance(content, str):
        session.prompts.append(content)
        return
    for block in _blocks(message):
        if block.get("type") == "text" and isinstance(block.get("text"), str):
            session.prompts.append(block["text"])
        elif block.get("type") == "tool_result":
            call = calls.get(str(block.get("tool_use_id") or ""))
            if call is not None:
                call.result_chars = _text_length(block.get("content"))
                call.is_error = bool(block.get("is_error"))
                call.answered = True


def _usage(raw: dict[str, Any]) -> Usage:
    split = raw.get("cache_creation") if isinstance(raw.get("cache_creation"), dict) else None
    total_write = _int(raw.get("cache_creation_input_tokens"))
    if split is not None:
        write_1h = _int(split.get("ephemeral_1h_input_tokens"))
        write_5m = _int(split.get("ephemeral_5m_input_tokens"))
    else:
        write_1h, write_5m = 0, total_write
    return Usage(
        input_tokens=_int(raw.get("input_tokens")),
        cache_write_5m=write_5m,
        cache_write_1h=write_1h,
        cache_read=_int(raw.get("cache_read_input_tokens")),
        output_tokens=_int(raw.get("output_tokens")),
    )


def _blocks(message: dict[str, Any]) -> list[dict[str, Any]]:
    content = message.get("content")
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def _text_length(content: Any) -> int:
    if isinstance(content, str):
        return len(content)
    if isinstance(content, list):
        return sum(
            len(part["text"])
            for part in content
            if isinstance(part, dict) and isinstance(part.get("text"), str)
        )
    return 0


def _int(value: Any) -> int:
    return value if isinstance(value, int) and value > 0 else 0
