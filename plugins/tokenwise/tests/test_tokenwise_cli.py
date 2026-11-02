from __future__ import annotations

import io
import json
from datetime import UTC, datetime
from pathlib import Path

from tokenwise.config.settings import Settings, settings_from
from tokenwise.connectors.files.store import project_slug
from tokenwise.core.model import Finding
from tokenwise.core.report import DIGEST_CAP_BYTES, build_metrics, render_digest
from tokenwise.entrypoints.cli.main import run
from tokenwise_helpers import Builder

NOW = datetime(2026, 11, 2, 9, 0, tzinfo=UTC)


def _setup(tmp_path: Path) -> tuple[Settings, Path, Path]:
    project = tmp_path / "app"
    project.mkdir()
    settings = Settings(tmp_path / "runs", tmp_path / "claude", auto_apply=True)
    folder = settings.claude_dir / "projects" / project_slug(project)
    builder = Builder()
    for _ in range(5):
        builder.tool("Bash", "x" * 25_000, command="pytest")
    builder.tool("Edit", "ok", file_path=str(project / "a.py"))
    transcript = builder.write(folder / "s1.jsonl")
    explorer = Builder(model="claude-opus-5-5")
    for _ in range(5):
        explorer.tool("Grep", "hit", pattern="x")
    explorer.write(folder / "s1" / "subagents" / "agent-1.jsonl")
    meta = folder / "s1" / "subagents" / "agent-1.meta.json"
    meta.write_text(json.dumps({"agentType": "Explore"}), encoding="utf-8")
    return settings, project, transcript


def _run(settings: Settings, *argv: str, stdin: str = "{}") -> tuple[int, str]:
    out = io.StringIO()
    code = run(list(argv), settings, io.StringIO(stdin), out, NOW)
    return code, out.getvalue()


def test_audit_apply_undo(tmp_path: Path) -> None:
    settings, project, _ = _setup(tmp_path)
    code, text = _run(settings, "--project", str(project), "audit", "--days", "3650")

    assert code == 0
    assert "1 sessions, 1 subagent runs" in text
    assert "LOW Cap Bash output" in text and len(text.splitlines()) <= 15
    data = settings.runs_root / project_slug(project).strip("-")
    digest = (data / "digest.md").read_text(encoding="utf-8")
    assert "Subagent Explore only reads" in digest

    code, text = _run(settings, "--project", str(project), "apply")
    local = project / ".claude" / "settings.local.json"
    assert json.loads(local.read_text())["env"] == {"BASH_MAX_OUTPUT_LENGTH": "15000"}
    assert "APPLIED env BASH_MAX_OUTPUT_LENGTH=15000" in text
    assert _run(settings, "--project", str(project), "apply")[1] == "Nothing new to apply.\n"

    code, text = _run(settings, "--project", str(project), "undo")
    assert json.loads(local.read_text())["env"] == {}
    assert "REVERTED" in text


def test_stop_hook_reports_new_findings_once_and_applies(tmp_path: Path) -> None:
    settings, project, transcript = _setup(tmp_path)
    payload = json.dumps(
        {"session_id": "s1", "transcript_path": str(transcript), "cwd": str(project)}
    )
    code, text = _run(settings, "hook", "stop", stdin=payload)

    message = json.loads(text)["systemMessage"]
    assert code == 0 and "new findings" in message and "BASH_MAX_OUTPUT_LENGTH" in message
    assert (project / ".claude" / "settings.local.json").is_file()
    assert _run(settings, "hook", "stop", stdin=payload) == (0, "")


def test_stop_hook_respects_auto_apply_off(tmp_path: Path) -> None:
    settings, project, transcript = _setup(tmp_path)
    off = Settings(settings.runs_root, settings.claude_dir, auto_apply=False)
    payload = json.dumps(
        {"session_id": "s1", "transcript_path": str(transcript), "cwd": str(project)}
    )
    _run(off, "hook", "stop", stdin=payload)
    assert not (project / ".claude" / "settings.local.json").exists()


def test_bash_hook_adds_context_at_third_failure(tmp_path: Path) -> None:
    settings, project, _ = _setup(tmp_path)
    failure = {
        "session_id": "s1",
        "cwd": str(project),
        "hook_event_name": "PostToolUseFailure",
        "tool_input": {"command": "make test"},
    }
    outputs = [
        _run(settings, "hook", "bash-result", stdin=json.dumps(failure))[1] for _ in range(3)
    ]
    assert outputs[:2] == ["", ""]
    reply = json.loads(outputs[2])["hookSpecificOutput"]
    assert reply["hookEventName"] == "PostToolUseFailure"
    assert "failed 3 times" in reply["additionalContext"]


def test_pre_compact_and_handoff_write_facts(tmp_path: Path) -> None:
    settings, project, transcript = _setup(tmp_path)
    payload = json.dumps(
        {"session_id": "s1", "transcript_path": str(transcript), "cwd": str(project)}
    )
    _, text = _run(settings, "hook", "pre-compact", stdin=payload)
    path = Path(json.loads(text)["systemMessage"].split("saved to ")[1])
    handoff = path.read_text(encoding="utf-8")
    assert "## Files changed" in handoff and "a.py` (1 edits)" in handoff
    assert "## State and next steps" in handoff

    code, text = _run(settings, "--project", str(project), "handoff")
    assert code == 0 and text.startswith("Handoff: ")


def test_digest_stays_under_cap() -> None:
    findings = [
        Finding("rule", f"k{i}", "medium", "t" * 200, "e" * 400, "a" * 400, i) for i in range(200)
    ]
    metrics = build_metrics("app", "now", [], findings, [])
    assert len(render_digest(metrics, findings).encode("utf-8")) <= DIGEST_CAP_BYTES


def test_settings_from_environment() -> None:
    settings = settings_from({"TOKENWISE_AUTO_APPLY": "0", "TOKENWISE_RUNS": "/r"})
    assert settings.auto_apply is False and settings.runs_root == Path("/r")
    assert settings_from({}).auto_apply is True
