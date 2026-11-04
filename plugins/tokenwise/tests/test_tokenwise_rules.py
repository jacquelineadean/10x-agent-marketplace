from __future__ import annotations

from tokenwise.core.model import Finding, Workspace
from tokenwise.core.project_rules import find_all, merge
from tokenwise.core.session_rules import session_findings
from tokenwise.core.usage import session_usage
from tokenwise_helpers import PROJECT, Builder


def _rules(builder: Builder, agent_type: str = "") -> dict[str, Finding]:
    session = builder.session(agent_type=agent_type)
    return {f.rule: f for f in session_findings(session, session_usage(session), PROJECT)}


def test_big_bash_output_offers_env_fix_at_five_calls() -> None:
    builder = Builder()
    for _ in range(4):
        builder.tool("Bash", "x" * 25_000, command="pytest")
    assert "bash-output-limit" not in _rules(builder)

    builder.tool("Bash", "x" * 25_000, command="pytest")
    finding = _rules(builder)["bash-output-limit"]
    assert finding.tier == "low"
    assert finding.fix == {
        "kind": "env",
        "name": "BASH_MAX_OUTPUT_LENGTH",
        "value": "15000",
    }


def test_generated_file_read_inside_project_gets_deny_rule() -> None:
    builder = Builder().tool("Read", "y" * 12_000, file_path=f"{PROJECT}/uv.lock")
    builder.tool("Read", "y" * 12_000, file_path="/elsewhere/uv.lock")
    builder.tool("Read", "y" * 12_000, file_path=f"{PROJECT}/src/app.py")
    findings = [f for f in _all(builder) if f.rule == "deny-generated-read"]
    assert [f.fix for f in findings] == [{"kind": "deny", "rule": "Read(./uv.lock)"}]


def test_retry_loop_needs_three_failures_of_one_command() -> None:
    builder = Builder()
    builder.tool("Bash", "err", is_error=True, command="make  test")
    builder.tool("Bash", "err", is_error=True, command="make test")
    assert "retry-loop" not in _rules(builder)
    builder.tool("Bash", "err", is_error=True, command="make test")
    assert "retry-loop" in _rules(builder)


def test_reread_counts_characters_after_first_read() -> None:
    builder = Builder()
    for _ in range(4):
        builder.tool("Read", "z" * 400, file_path=f"{PROJECT}/a.py")
    finding = _rules(builder)["reread"]
    assert finding.at_stake == 300  # 3 reads after the first, 400 characters each, / 4


def test_context_peak_only_for_main_sessions() -> None:
    builder = Builder().respond(context=160_000)
    assert "context-peak" in _rules(builder)
    assert "context-peak" not in _rules(builder, agent_type="Explore")


def test_cache_miss_names_model_switch() -> None:
    builder = Builder()
    for _ in range(20):
        builder.respond(context=30_000, cache_read=5_000, cache_write=24_998)
    builder.model = "claude-opus-5-5"
    builder.respond(context=30_000, cache_read=5_000, cache_write=24_998)
    finding = _rules(builder)["cache-miss"]
    assert "2 models used" in finding.evidence


def test_exploration_in_main_skipped_when_subagent_used() -> None:
    builder = Builder()
    for i in range(30):
        builder.tool("Grep", "hit", pattern=f"p{i}")
    assert "explore-in-main" in _rules(builder)
    builder.tool("Agent", "summary", prompt="find it")
    assert "explore-in-main" not in _rules(builder)


def test_downgrade_large_model_without_file_changes() -> None:
    builder = Builder(model="claude-opus-5-5")
    for _ in range(4):
        builder.tool("Read", "a", file_path=f"{PROJECT}/a.py")
    assert "downgrade-model" not in _rules(builder)  # too short to judge
    builder.respond()
    assert "downgrade-model" in _rules(builder)
    builder.tool("Bash", "", command="cat > notes.md <<'EOF'")
    assert "downgrade-model" not in _rules(builder)
    assert "downgrade-model" not in _rules(Builder().tool("Read", "a", file_path="/x"))


def test_read_only_subagent_on_large_model_suggests_haiku() -> None:
    builder = Builder(model="claude-opus-5-5")
    for _ in range(5):
        builder.tool("Grep", "hit", pattern="x")
    finding = _rules(builder, agent_type="Explore")["subagent-model"]
    assert finding.key == "Explore"


def test_output_heavy_needs_volume_and_share() -> None:
    builder = Builder().respond(output=25_000, context=10_000)
    assert "output-heavy" in _rules(builder)
    assert "output-heavy" not in _rules(Builder().respond(output=5_000, context=1_000))


def test_project_rules_repeated_command_instructions_and_unused_mcp() -> None:
    sessions = []
    for i in range(3):
        builder = Builder().tool("Bash", "ok", command="uv run pytest plugins/x -q")
        builder.tool("mcp__github__get_me", "{}")
        sessions.append(builder.session(f"s{i}"))
    workspace = Workspace(PROJECT, {"CLAUDE.md": 20_000}, ("github", "slack"))
    usages = {s.id: session_usage(s) for s in sessions}
    by_rule = {f.rule: f for f in find_all(sessions, usages, workspace)}

    assert by_rule["repeated-command"].sessions == ("s0", "s1", "s2")
    assert by_rule["instruction-size"].tier == "high"
    assert by_rule["unused-mcp"].key == "slack"


def test_findings_ranked_by_tier_then_tokens() -> None:
    builder = Builder(model="claude-opus-5-5").respond(context=160_000)
    for _ in range(5):
        builder.tool("Bash", "x" * 25_000, command="ls -R")
    workspace = Workspace(PROJECT, {"AGENTS.md": 40_000})
    session = builder.session()
    tiers = [f.tier for f in find_all([session], {"s1": session_usage(session)}, workspace)]
    assert tiers == sorted(tiers, key=["low", "medium", "high"].index)


def test_merge_sums_tokens_and_joins_sessions() -> None:
    one = Builder().tool("Read", "y" * 12_000, file_path=f"{PROJECT}/uv.lock")
    a = session_findings(one.session("a"), session_usage(one.session("a")), PROJECT)
    b = session_findings(one.session("b"), session_usage(one.session("b")), PROJECT)
    (merged,) = [f for f in merge(a + b) if f.rule == "deny-generated-read"]
    assert merged.sessions == ("a", "b")
    assert merged.at_stake == 6_000
    assert merged.evidence.endswith("in 2 sessions")


def _all(builder: Builder) -> list[Finding]:
    session = builder.session()
    return session_findings(session, session_usage(session), PROJECT)
