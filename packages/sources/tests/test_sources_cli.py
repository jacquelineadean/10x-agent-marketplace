"""The sources command line against a temporary config folder and run folder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sources.core import agent
from sources.entrypoints.cli.main import main
from sources_helpers import facts, queries


@pytest.fixture(autouse=True)
def _home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Own config folders and no keys, so the user's machine never leaks into a test."""
    monkeypatch.setenv("SOURCES_CONNECTIONS", str(tmp_path / "config" / "connections.json"))
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path / "claude"))
    monkeypatch.setenv("PATH", str(tmp_path / "bin"))
    for name in ("GITHUB_TOKEN", "GH_TOKEN", "DD_API_KEY", "DD_APP_KEY", "DATABASE_URL"):
        monkeypatch.delenv(name, raising=False)


def test_detect_prints_one_line_per_system(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["detect", "--connectors", "github,claude_ai_Atlassian"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert len(lines) == 9
    assert lines[0] == "GitHub: connected through github"
    assert lines[1] == "Jira: connected through claude_ai_Atlassian"
    assert lines[-1] == "Oracle: not set up: run /sources:connect"


def test_detect_picker_is_ask_user_question_input(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DD_API_KEY", "x")
    monkeypatch.setenv("DD_APP_KEY", "y")
    assert main(["detect", "--picker"]) == 0
    questions = json.loads(capsys.readouterr().out)
    datadog = questions[1]["options"][0]
    assert datadog == {
        "label": "Datadog",
        "description": "DD_API_KEY and DD_APP_KEY set; script collector ready",
    }


def test_connections_add_list_and_remove(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    args = [
        "connection",
        "add",
        "warehouse",
        "--system",
        "postgres",
        "--host",
        "db:5432",
        "--database",
        "analytics",
        "--env",
        "user=PGUSER",
        "--env",
        "password=PGPASSWORD",
    ]
    assert main(args) == 0
    saved = json.loads((tmp_path / "config" / "connections.json").read_text(encoding="utf-8"))
    assert saved["connections"]["warehouse"]["env"] == {"user": "PGUSER", "password": "PGPASSWORD"}
    assert main(["connection", "list"]) == 0
    assert "warehouse: postgres at db:5432/analytics" in capsys.readouterr().out
    assert main(["detect"]) == 0
    assert "Postgres: connection warehouse; no connector in this session" in capsys.readouterr().out
    assert main(["connection", "remove", "warehouse"]) == 0
    assert main(["connection", "remove", "warehouse"]) == 1


def test_a_pasted_key_is_refused(capsys: pytest.CaptureFixture[str]) -> None:
    args = [
        "connection",
        "add",
        "warehouse",
        "--system",
        "postgres",
        "--host",
        "db",
        "--env",
        "password=hunter2",
    ]
    assert main(args) == 1
    err = capsys.readouterr().err
    assert "never hold the key itself" in err and "hunter2" not in err


def test_digest_checks_then_writes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    run = tmp_path / "run"
    run.mkdir()
    (run / "facts.json").write_text(json.dumps(facts()), encoding="utf-8")
    q = queries()
    del q["queries"]["jira.epics_done"]
    (run / "queries.json").write_text(json.dumps(q), encoding="utf-8")
    assert main(["digest", str(run)]) == 1
    assert "jira.epics_done: no entry in queries.json" in capsys.readouterr().err
    assert not (run / "digest.md").exists()
    (run / "queries.json").write_text(json.dumps(queries()), encoding="utf-8")
    assert main(["check", str(run)]) == 0
    assert main(["digest", str(run)]) == 0
    assert (run / "digest.md").read_text(encoding="utf-8").startswith("# Digest")


def test_agent_writes_a_user_level_database_agent(tmp_path: Path) -> None:
    for name, system, host, env in (
        ("warehouse", "postgres", "db:5432", ["user=PGUSER", "password=PGPASSWORD"]),
        ("lake", "databricks", "https://acme.cloud.databricks.com", ["token=DATABRICKS_TOKEN"]),
        ("tracker", "jira", "https://acme.atlassian.net", []),
    ):
        extra = [f"--env={e}" for e in env]
        add = ["connection", "add", name, "--system", system, "--host", host, *extra]
        assert main([*add, "--database", "analytics"] if system == "postgres" else add) == 0
    assert main(["agent"]) == 0
    text = (tmp_path / "claude" / "agents" / agent.FILE).read_text(encoding="utf-8")
    assert agent.systems_in(text) == {"postgres", "databricks"}
    assert '"postgresql://db:5432/analytics"' in text and '"${PGPASSWORD}"' in text
    assert '"--access-mode=restricted"' in text
    assert '"https://acme.cloud.databricks.com/api/2.0/mcp/sql"' in text
    assert "tracker" not in text
    assert main(["agent"]) == 1  # an existing file needs --force
    assert main(["agent", "--connection", "nope", "--force"]) == 1
    assert main(["detect"]) == 0


def test_gather_on_a_folder_with_no_script_entries_only_writes_the_digest(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "facts.json").write_text(json.dumps(facts()))
    (tmp_path / "queries.json").write_text(json.dumps(queries()))
    assert main(["gather", str(tmp_path), "--until", "2026-10-31"]) == 0
    assert capsys.readouterr().out.startswith(f"wrote {tmp_path / 'digest.md'}")
    assert "Lane mcp" in (tmp_path / "digest.md").read_text()
