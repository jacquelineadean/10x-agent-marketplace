"""`sources gather` on a run folder: facts written, entries stamped, failures kept apart."""

from __future__ import annotations

import io
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from sources.entrypoints.cli import gather
from sources_helpers import FakeProgram, FakeWeb, Reply, facts, fixture, queries, text_fixture, wire

Q3 = {"start": "2026-07-01", "end": "2026-09-30"}


def _folder(tmp_path: Path) -> Path:
    run = tmp_path / "run"
    run.mkdir()
    plan = queries()
    plan["queries"].update(
        {
            "jira.resolved": {
                "system": "jira",
                "lane": "script",
                "connection": "jira",
                "request": {"jql": "project = SHOP", "date": "resolved", "per": "month"},
                "window": Q3,
            },
            "datadog.p95": {
                "system": "datadog",
                "lane": "script",
                "connection": "datadog",
                "request": {
                    "metric": "p95:trace.http.request.duration{service:checkout}",
                    "unit": "ms",
                    "note": "checkout p95, average of days",
                },
                "window": {"start": "2026-07-01", "end": "2026-08-31"},
            },
            "postgres.orders": {
                "system": "postgres",
                "lane": "script",
                "connection": "postgres",
                "request": {"sql": "SELECT month, orders, revenue, first FROM monthly"},
                "window": Q3,
            },
            "servicenow.p1": {
                "system": "servicenow",
                "lane": "script",
                "connection": "servicenow",
                "request": {"table": "incident", "query": "priority=1"},
                "window": Q3,
            },
        }
    )
    (run / "facts.json").write_text(json.dumps(facts()))
    (run / "queries.json").write_text(json.dumps(plan))
    return run


def _run(run: Path, tmp_path: Path, **options: Any) -> tuple[int, str, str]:
    web = FakeWeb()
    web.on(
        "POST",
        "/rest/api/3/search/approximate-count",
        Reply(fixture("jira/approximate_count.json")),
    )
    web.on("GET", "/api/v1/query", Reply(fixture("datadog/query_daily.json")))
    program = FakeProgram(stdout=text_fixture("postgres/rows.json"))
    environ = {
        "SOURCES_CONNECTIONS": str(tmp_path / "connections.json"),
        "JIRA_URL": "https://acme.atlassian.net",
        "JIRA_EMAIL": "a@b.c",
        "JIRA_API_TOKEN": "jira-secret",
        "DD_API_KEY": "dd-secret",
        "DD_APP_KEY": "dd-app",
        "DATABASE_URL": "postgresql://reader:pg-secret@db/shop",
    }
    out, err = io.StringIO(), io.StringIO()
    code = gather.run(run, wire=wire(web, program, **environ), out=out, err=err, **options)
    return code, out.getvalue(), err.getvalue()


def test_gather_writes_each_result_at_its_path_and_stamps_its_entry(tmp_path: Path) -> None:
    run = _folder(tmp_path)
    code, out, err = _run(run, tmp_path, until=date(2026, 10, 31))
    assert code == 1  # servicenow has no keys
    assert err.splitlines() == [
        "error: servicenow.p1: servicenow (servicenow) needs SERVICENOW_INSTANCE set"
    ]
    assert out.splitlines()[:3] == [
        "jira.resolved: 3 rows x 2 columns, 2026-07-01..2026-09-30, as of 2026-10-31",
        "datadog.p95: 1 value, 2026-07-01..2026-08-31, as of 2026-10-31",
        "postgres.orders: 3 rows x 4 columns, 2026-07-01..2026-09-30, as of 2026-10-31",
    ]
    assert "secret" not in out + err and "44964" not in out
    written = json.loads((run / "facts.json").read_text())
    assert written["github"] == facts()["github"]
    assert written["jira"]["resolved"] == {
        "month": ["2026-07", "2026-08", "2026-09"],
        "count": [57, 57, 57],
    }
    assert written["datadog"]["p95"] == {
        "value": 254.51612903225808,
        "source": "datadog",
        "unit": "ms",
        "note": "checkout p95, average of days, 2026-07-01..2026-08-31",
    }
    assert written["postgres"]["orders"]["orders"] == [905, 905, 875]
    entries = json.loads((run / "queries.json").read_text())["queries"]
    assert entries["jira.resolved"]["as_of"] == "2026-10-31"
    assert entries["jira.resolved"]["query"].startswith("JQL (project = SHOP) AND resolved >=")
    assert "as_of" not in entries["servicenow.p1"]
    digest = (run / "digest.md").read_text()
    assert "`jira.resolved.count`" in digest and "servicenow" not in digest


def test_a_refresh_rolls_windows_and_marks_the_folder_refreshed(tmp_path: Path) -> None:
    run = _folder(tmp_path)
    _run(run, tmp_path, until=date(2026, 10, 31))
    code, out, _ = _run(run, tmp_path, roll=True, until=date(2026, 11, 1), paths=["jira.resolved"])
    assert code == 0
    assert out.splitlines()[0] == (
        "jira.resolved: 3 rows x 2 columns, 2026-08-01..2026-10-31, as of 2026-11-01"
    )
    plan = json.loads((run / "queries.json").read_text())
    assert plan["refreshed"] == "2026-11-01"
    assert plan["queries"]["jira.resolved"]["window"] == {
        "start": "2026-08-01",
        "end": "2026-10-31",
    }
    assert plan["queries"]["datadog.p95"]["as_of"] == "2026-10-31"
    assert plan["queries"]["github"]["lane"] == "mcp"
    resolved = json.loads((run / "facts.json").read_text())["jira"]["resolved"]
    assert resolved["month"] == ["2026-08", "2026-09", "2026-10"]
    digest = (run / "digest.md").read_text()
    assert (
        "## github\nLane mcp through github; as of 2026-10-31. Not refreshed on 2026-11-01"
        in digest
    )
    assert (
        "## jira\nLane mcp, script through claude_ai_Atlassian, jira; "
        "as of 2026-10-31 to 2026-11-01." in digest
    )


def test_a_future_as_of_date_is_refused(tmp_path: Path) -> None:
    run = _folder(tmp_path)
    code, _, err = _run(run, tmp_path, until=date.today() + timedelta(days=1))
    assert code == 1 and "later than today" in err
