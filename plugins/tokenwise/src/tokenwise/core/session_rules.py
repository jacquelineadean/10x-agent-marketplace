"""Rules that judge one session at a time. Each returns findings with evidence and a tier.

Low tier: safe and reversible; some carry a `fix` that `apply` writes to
`.claude/settings.local.json`. Medium tier changes how work runs; the user decides.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from pathlib import PurePosixPath
from typing import Any

from tokenwise.core.model import EDIT_TOOLS_NAMES as EDIT_TOOLS
from tokenwise.core.model import Finding, Session, ToolCall
from tokenwise.core.usage import cache_read_weight

BIG_BASH_CHARS = 20_000
BIG_BASH_MIN_CALLS = 5
BASH_LIMIT = "15000"  # half of Claude Code's 30,000-character default
GENERATED_MIN_CHARS = 10_000
RETRY_MIN_FAILURES = 3
REREAD_MIN = 4
PEAK_CONTEXT = 150_000
CLEAR_FLOOR = 50_000
CACHE_MIN_RESPONSES = 20
CACHE_MIN_HIT = 0.7
EXPLORE_MIN_CALLS = 30
DOWNGRADE_MIN_RESPONSES = 5
DOWNGRADE_MAX_RESPONSES = 40
OUTPUT_MIN_TOKENS = 20_000
OUTPUT_MIN_SHARE = 0.5
BIG_MCP_CHARS = 40_000
LARGE_MODELS = ("opus", "fable")
SEARCH_TOOLS = frozenset({"Read", "Grep", "Glob"})
READ_ONLY_TOOLS = SEARCH_TOOLS | {"WebFetch", "WebSearch", "LS", "ToolSearch", "SubagentHandback"}
SHELL_WRITES = re.compile(r">>?\s|<<|sed -i|\btee\b|git (commit|push|rm|mv)|\brm\b|\bmv\b|\bcp\b")
DELEGATE_TOOLS = frozenset({"Agent", "Task"})
GENERATED = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|uv\.lock|poetry\.lock|Cargo\.lock|"
    r"Gemfile\.lock|composer\.lock|go\.sum)$"
    r"|\.(min\.js|min\.css|map|lock)$"
    r"|(^|/)(node_modules|dist|build|\.next|coverage)/"
)


def session_findings(session: Session, usage: dict[str, Any], project_dir: str) -> list[Finding]:
    return [
        *big_bash_output(session),
        *generated_reads(session, project_dir),
        *retry_loops(session, usage),
        *rereads(session),
        *big_mcp_output(session),
        *context_peak(session, usage),
        *cache_misses(session, usage),
        *exploration_in_main(session),
        *downgrade(session, usage),
        *output_heavy(session, usage),
    ]


def big_bash_output(session: Session) -> list[Finding]:
    big = [c for c in session.tools if c.name == "Bash" and c.result_chars >= BIG_BASH_CHARS]
    if len(big) < BIG_BASH_MIN_CALLS:
        return []
    return [
        Finding(
            rule="bash-output-limit",
            key=session.id,
            tier="low",
            title="Cap Bash output at 15,000 characters",
            evidence=f"{len(big)} Bash results of {BIG_BASH_CHARS:,}+ characters in one session",
            advice="Pipe noisy commands through `tail` or `grep`; run tests in quiet mode.",
            at_stake=sum(c.result_chars - int(BASH_LIMIT) for c in big) // 4,
            sessions=(session.id,),
            fix={"kind": "env", "name": "BASH_MAX_OUTPUT_LENGTH", "value": BASH_LIMIT},
        )
    ]


def generated_reads(session: Session, project_dir: str) -> list[Finding]:
    found = []
    for path, calls in _group(session.tools, "Read").items():
        relative = _relative(path, project_dir)
        chars = sum(c.result_chars for c in calls)
        if relative is None or not GENERATED.search(relative) or chars < GENERATED_MIN_CHARS:
            continue
        found.append(
            Finding(
                rule="deny-generated-read",
                key=relative,
                tier="low",
                title=f"Stop reading generated file {relative}",
                evidence=f"{len(calls)} reads, {chars:,} characters into context",
                advice="Query it with grep or a script when an answer is needed from it.",
                at_stake=chars // 4,
                sessions=(session.id,),
                fix={"kind": "deny", "rule": f"Read(./{relative})"},
            )
        )
    return found


def retry_loops(session: Session, usage: dict[str, Any]) -> list[Finding]:
    failures = Counter(c.command for c in session.tools if c.name == "Bash" and c.is_error)
    found = []
    for command, count in failures.items():
        if count < RETRY_MIN_FAILURES:
            continue
        found.append(
            Finding(
                rule="retry-loop",
                key=f"{session.id}:{command[:60]}",
                tier="low",
                title="Same command failed repeatedly",
                evidence=f"`{_short(command)}` failed {count} times in one session",
                advice="Fix the cause once: a missing tool, path or setup step goes in "
                "AGENTS.md or a script. The loop-guard hook now warns at the third failure.",
                at_stake=count * usage["peak_context"] // 10,
                sessions=(session.id,),
            )
        )
    return found


def rereads(session: Session) -> list[Finding]:
    found = []
    for path, calls in _group(session.tools, "Read").items():
        if len(calls) < REREAD_MIN:
            continue
        extra = sum(c.result_chars for c in calls[1:])
        found.append(
            Finding(
                rule="reread",
                key=f"{session.id}:{path}",
                tier="low",
                title=f"File read {len(calls)} times: {PurePosixPath(path).name}",
                evidence=f"{len(calls)} reads of {path}, {extra:,} characters after the first",
                advice="Read once with offset and limit; edits do not need a re-read.",
                at_stake=extra // 4,
                sessions=(session.id,),
            )
        )
    return found


def big_mcp_output(session: Session) -> list[Finding]:
    by_server: dict[str, list[ToolCall]] = defaultdict(list)
    for call in session.tools:
        if call.name.startswith("mcp__") and call.result_chars >= BIG_MCP_CHARS:
            by_server[call.name.split("__")[1]].append(call)
    return [
        Finding(
            rule="mcp-output",
            key=f"{session.id}:{server}",
            tier="medium",
            title=f"MCP server {server} returns large results",
            evidence=f"{len(calls)} results of {BIG_MCP_CHARS:,}+ characters",
            advice="Ask for narrower queries or fewer fields, run the tool inside a subagent, "
            "or lower MAX_MCP_OUTPUT_TOKENS (default 25,000).",
            at_stake=sum(c.result_chars for c in calls) // 4,
            sessions=(session.id,),
        )
        for server, calls in by_server.items()
    ]


def context_peak(session: Session, usage: dict[str, Any]) -> list[Finding]:
    if session.is_subagent or usage["peak_context"] < PEAK_CONTEXT:
        return []
    over = sum(
        (r.usage.context - CLEAR_FLOOR) * cache_read_weight(r.model)
        for r in session.responses
        if r.usage.context > CLEAR_FLOOR
    )
    return [
        Finding(
            rule="context-peak",
            key=session.id,
            tier="medium",
            title="Context grew past 150,000 tokens",
            evidence=f"peak {usage['peak_context']:,} tokens over {usage['responses']} responses",
            advice="Start a new session per task: `/tokenwise:handoff`, then `/clear`. "
            "A handoff file costs less than `/compact`, which re-reads the whole context.",
            at_stake=round(over),
            sessions=(session.id,),
        )
    ]


def cache_misses(session: Session, usage: dict[str, Any]) -> list[Finding]:
    if usage["responses"] < CACHE_MIN_RESPONSES or usage["cache_hit"] >= CACHE_MIN_HIT:
        return []
    models = usage["models"]
    cause = (
        f"; {len(models)} models used, and a switch rebuilds the cache" if len(models) > 1 else ""
    )
    return [
        Finding(
            rule="cache-miss",
            key=session.id,
            tier="medium",
            title="Prompt cache missed often",
            evidence=f"{usage['cache_hit']:.0%} of context came from cache{cause}",
            advice="Keep CLAUDE.md, MCP servers and the model fixed during a session; "
            "pauses over 5 minutes expire the default cache.",
            at_stake=usage["cache_write_tokens"] // 4,
            sessions=(session.id,),
        )
    ]


def exploration_in_main(session: Session) -> list[Finding]:
    if session.is_subagent or any(c.name in DELEGATE_TOOLS for c in session.tools):
        return []
    search = [c for c in session.tools if c.name in SEARCH_TOOLS]
    if len(search) < EXPLORE_MIN_CALLS:
        return []
    chars = sum(c.result_chars for c in search)
    return [
        Finding(
            rule="explore-in-main",
            key=session.id,
            tier="medium",
            title="Searches ran in the main conversation",
            evidence=f"{len(search)} Read, Grep and Glob calls, {chars:,} characters, no subagent",
            advice="Send broad searches to the Explore subagent; only its summary returns.",
            at_stake=chars // 4,
            sessions=(session.id,),
        )
    ]


def downgrade(session: Session, usage: dict[str, Any]) -> list[Finding]:
    model = max(usage["models"], key=usage["models"].get, default="")
    if not _large(model) or not (
        DOWNGRADE_MIN_RESPONSES <= usage["responses"] <= DOWNGRADE_MAX_RESPONSES
    ):
        return []
    names = {c.name for c in session.tools}
    if session.is_subagent:
        if not names <= READ_ONLY_TOOLS:
            return []
        return [_subagent_downgrade(session, usage, model)]
    if names & EDIT_TOOLS or any(SHELL_WRITES.search(c.command) for c in session.tools):
        return []
    effort = max(usage["efforts"], key=usage["efforts"].get, default="default")
    return [
        Finding(
            rule="downgrade-model",
            key=session.id,
            tier="medium",
            title="Read-only session on a large model",
            evidence=f"{model} at effort {effort}, {usage['responses']} responses, no file changes",
            advice="Use Sonnet or a lower effort for questions and reviews: `/model sonnet` or "
            "`/effort low`. Keep the large model for multi-file changes.",
            at_stake=usage["weighted_tokens"] // 2,
            sessions=(session.id,),
        )
    ]


def output_heavy(session: Session, usage: dict[str, Any]) -> list[Finding]:
    if usage["output_tokens"] < OUTPUT_MIN_TOKENS or usage["output_share"] < OUTPUT_MIN_SHARE:
        return []
    return [
        Finding(
            rule="output-heavy",
            key=session.id,
            tier="medium",
            title="Output tokens dominate cost",
            evidence=f"{usage['output_tokens']:,} output tokens, "
            f"{usage['output_share']:.0%} of weighted cost; output costs 5x input",
            advice="Use a terse output style; ask for diffs and edits over full-file rewrites.",
            at_stake=usage["output_tokens"] * 5 * 3 // 10,
            sessions=(session.id,),
        )
    ]


def _subagent_downgrade(session: Session, usage: dict[str, Any], model: str) -> Finding:
    return Finding(
        rule="subagent-model",
        key=session.agent_type,
        tier="medium",
        title=f"Subagent {session.agent_type} only reads, on {model}",
        evidence=f"{usage['responses']} responses using read-only tools",
        advice=f"Set `model: haiku` in the {session.agent_type} agent definition, "
        "or pass a smaller model when spawning it.",
        at_stake=usage["weighted_tokens"] * 3 // 4,
        sessions=(session.id,),
    )


def _group(calls: list[ToolCall], tool: str) -> dict[str, list[ToolCall]]:
    grouped: dict[str, list[ToolCall]] = defaultdict(list)
    for call in calls:
        if call.name == tool and call.path and not call.is_error:
            grouped[call.path].append(call)
    return grouped


def _relative(path: str, project_dir: str) -> str | None:
    root = project_dir.rstrip("/") + "/"
    if not project_dir or not path.startswith(root):
        return None
    return path[len(root) :]


def _large(model: str) -> bool:
    return any(name in model for name in LARGE_MODELS)


def _short(command: str) -> str:
    return command if len(command) <= 80 else command[:77] + "..."
