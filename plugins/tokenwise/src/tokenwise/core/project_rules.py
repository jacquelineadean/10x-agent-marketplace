"""Rules across many sessions and the project's files, and the merge that ranks findings.

High tier: changes to files every session loads (instructions, MCP servers). Recommended
with evidence, never applied by code: editing them mid-session also rebuilds the cache.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import Any

from tokenwise.core.model import TIERS, Finding, Session, Workspace
from tokenwise.core.session_rules import session_findings

REPEAT_MIN_SESSIONS = 3
REPEAT_MIN_LENGTH = 20
TRIVIAL_COMMANDS = ("ls", "cd ", "pwd", "cat ", "git status", "git diff", "git log", "echo ")
INSTRUCTIONS_MAX_BYTES = 12_000
MCP_MIN_SESSIONS = 3


def find_all(
    sessions: list[Session], usages: dict[str, dict[str, Any]], workspace: Workspace
) -> list[Finding]:
    found: list[Finding] = []
    for session in sessions:
        found.extend(session_findings(session, usages[session.id], workspace.project_dir))
    found.extend(repeated_commands(sessions))
    found.extend(instruction_size(sessions, workspace))
    found.extend(unused_mcp(sessions, workspace))
    return rank(merge(found))


def repeated_commands(sessions: list[Session]) -> list[Finding]:
    seen: dict[str, set[str]] = defaultdict(set)
    chars: dict[str, int] = defaultdict(int)
    for session in sessions:
        for call in session.tools:
            command = call.command
            if len(command) < REPEAT_MIN_LENGTH or command.startswith(TRIVIAL_COMMANDS):
                continue
            seen[command].add(session.id)
            chars[command] += call.result_chars
    return [
        Finding(
            rule="repeated-command",
            key=command[:80],
            tier="medium",
            title="Same command typed in many sessions",
            evidence=f"`{command[:80]}` ran in {len(ids)} sessions",
            advice="Put it in a script, a skill or the AGENTS.md command list so Claude "
            "stops rediscovering it.",
            at_stake=chars[command] // 4 + 200 * len(ids),
            sessions=tuple(sorted(ids)),
        )
        for command, ids in seen.items()
        if len(ids) >= REPEAT_MIN_SESSIONS
    ]


def instruction_size(sessions: list[Session], workspace: Workspace) -> list[Finding]:
    total = sum(workspace.instruction_files.values())
    if total <= INSTRUCTIONS_MAX_BYTES:
        return []
    files = ", ".join(f"{name} {size:,} B" for name, size in workspace.instruction_files.items())
    responses = sum(len(s.responses) for s in sessions if not s.is_subagent)
    return [
        Finding(
            rule="instruction-size",
            key="instructions",
            tier="high",
            title="Instruction files load on every turn",
            evidence=f"{total:,} bytes, about {total // 4:,} tokens per session ({files})",
            advice="Keep rules every task needs; move procedures used by some tasks into "
            "skills, which load only when invoked. Edit between sessions.",
            at_stake=(total - INSTRUCTIONS_MAX_BYTES) // 4 * responses // 10,
        )
    ]


def unused_mcp(sessions: list[Session], workspace: Workspace) -> list[Finding]:
    main = [s for s in sessions if not s.is_subagent]
    if len(main) < MCP_MIN_SESSIONS:
        return []
    used = {c.name.split("__")[1] for s in sessions for c in s.tools if c.name.startswith("mcp__")}
    return [
        Finding(
            rule="unused-mcp",
            key=server,
            tier="high",
            title=f"MCP server {server} never used",
            evidence=f"no {server} tool calls in {len(main)} sessions",
            advice="Disable it in `.mcp.json` or with `/mcp`; its tool list loads every session "
            "unless tool search defers it.",
            at_stake=0,
        )
        for server in workspace.mcp_servers
        if server not in used
    ]


def merge(findings: list[Finding]) -> list[Finding]:
    """One finding per id: sessions joined, tokens at stake summed."""
    groups: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        groups[finding.id].append(finding)
    merged = []
    for group in groups.values():
        first = group[0]
        if len(group) == 1:
            merged.append(first)
            continue
        sessions = tuple(sorted({s for f in group for s in f.sessions}))
        merged.append(
            replace(
                first,
                at_stake=sum(f.at_stake for f in group),
                sessions=sessions,
                evidence=f"{first.evidence}; in {len(sessions)} sessions",
            )
        )
    return merged


def rank(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (TIERS.index(f.tier), -f.at_stake, f.id))
