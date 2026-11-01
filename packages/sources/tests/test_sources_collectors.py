"""Each HTTPS collector against recorded replies: the requests it sends and what it returns."""

from __future__ import annotations

from datetime import date

import pytest
from sources.connectors import atlassian, databricks, datadog, pagerduty, servicenow
from sources.connectors.errors import AuthError, SourceError
from sources.connectors.github import counts
from sources.connectors.http import JsonTransport
from sources.core.collect import RequestError
from sources.core.periods import Window
from sources.core.reach import Reach, ReachError, reach
from sources.core.sql import SqlError
from sources_helpers import FakeWeb, Reply, fixture, wire

Q3 = Window(date(2026, 7, 1), date(2026, 9, 30))
JUL_AUG = Window(date(2026, 7, 1), date(2026, 8, 31))


def _reach(system: str, environ: dict[str, str]) -> Reach:
    return reach(system, system, {}, environ)


def test_github_counts_search_results_per_month_with_the_date_qualifier() -> None:
    web = FakeWeb()
    for month, end in (("jul", "07-31"), ("aug", "08-31"), ("sep", "09-30")):
        start = {"jul": "07-01", "aug": "08-01", "sep": "09-01"}[month]
        q = f"is:pr is:merged org:acme merged:2026-{start}..2026-{end}"
        web.on(
            "GET",
            "/search/issues",
            Reply(fixture(f"github/search_merged_{month}.json")),
            where={"q": q},
        )
    request = {"search": "is:pr is:merged org:acme", "date": "merged", "per": "month"}
    result = counts.read(request, Q3, _reach("github", {"GITHUB_TOKEN": "ghp_x"}), wire(web))
    assert result.table == {"month": ["2026-07", "2026-08", "2026-09"], "count": [412, 388, 455]}
    assert result.query == (
        'search/issues q="is:pr is:merged org:acme merged:2026-07-01..2026-09-30" per month'
    )
    assert all(s.params["per_page"] == ["1"] for s in web.sent)
    assert web.sent[0].headers["Authorization"] == "Bearer ghp_x"


def test_github_counts_workflow_runs_and_warns_on_partial_search() -> None:
    web = FakeWeb().on(
        "GET",
        "/repos/acme/shop/actions/workflows/deploy.yml/runs",
        Reply(fixture("github/runs_deploy.json")),
    )
    request = {"runs": "acme/shop", "workflow": "deploy.yml"}
    result = counts.read(request, Q3, _reach("github", {"GH_TOKEN": "t"}), wire(web))
    assert result.value == 61
    assert web.sent[0].params["created"] == ["2026-07-01..2026-09-30"]
    assert web.sent[0].params["status"] == ["success"]
    web = FakeWeb().on("GET", "/search/issues", Reply(fixture("github/search_incomplete.json")))
    partial = counts.read(
        {"search": "is:issue"}, Q3, _reach("github", {"GH_TOKEN": "t"}), wire(web)
    )
    assert partial.value == 97 and "may be low" in partial.warnings[0]
    with pytest.raises(RequestError, match="window sets it"):
        counts.read(
            {"search": "is:pr created:>2026"}, Q3, _reach("github", {"GH_TOKEN": "t"}), wire()
        )


def test_jira_cloud_counts_through_the_read_only_count_post() -> None:
    web = FakeWeb().on(
        "POST",
        "/rest/api/3/search/approximate-count",
        Reply(fixture("jira/approximate_count.json")),
    )
    where = _reach(
        "jira",
        {"JIRA_URL": "https://acme.atlassian.net", "JIRA_EMAIL": "a@b.c", "JIRA_API_TOKEN": "tok"},
    )
    request = {
        "jql": "project = SHOP AND statusCategory = Done ORDER BY resolved",
        "date": "resolved",
    }
    result = atlassian.jira(request, Q3, where, wire(web))
    assert result.value == 57
    assert web.sent[0].body == {
        "jql": '(project = SHOP AND statusCategory = Done) AND resolved >= "2026-07-01" '
        'AND resolved < "2026-10-01"'
    }
    assert web.sent[0].headers["Authorization"].startswith("Basic ")


def test_jira_data_center_counts_through_search_get() -> None:
    web = FakeWeb().on("GET", "/rest/api/2/search", Reply(fixture("jira/search_dc.json")))
    where = _reach(
        "jira", {"JIRA_URL": "jira.acme.internal", "JIRA_EMAIL": "a", "JIRA_API_TOKEN": "t"}
    )
    assert atlassian.jira({"jql": "project = OPS"}, Q3, where, wire(web)).value == 143
    assert web.sent[0].params["maxResults"] == ["0"]


def test_confluence_counts_pages_under_wiki_on_cloud() -> None:
    web = FakeWeb().on("GET", "/wiki/rest/api/search", Reply(fixture("confluence/search.json")))
    where = _reach(
        "confluence",
        {
            "CONFLUENCE_URL": "https://acme.atlassian.net",
            "CONFLUENCE_EMAIL": "a@b.c",
            "CONFLUENCE_API_TOKEN": "t",
        },
    )
    result = atlassian.confluence({"cql": "space = ENG AND type = page"}, Q3, where, wire(web))
    assert result.value == 38
    assert web.sent[0].params["cql"] == [
        '(space = ENG AND type = page) AND created >= "2026-07-01" AND created < "2026-10-01"'
    ]


def test_datadog_reduces_daily_rollups_per_period_in_code() -> None:
    web = FakeWeb().on("GET", "/api/v1/query", Reply(fixture("datadog/query_daily.json")))
    where = _reach("datadog", {"DD_API_KEY": "k", "DD_APP_KEY": "a", "DD_SITE": "datadoghq.eu"})
    request = {"metric": "p95:trace.http.request.duration{service:checkout}", "per": "month"}
    result = datadog.read({**request, "reduce": "max"}, JUL_AUG, where, wire(web))
    assert result.table == {"month": ["2026-07", "2026-08"], "max": [260.0, 310.0]}
    sent = web.sent[0]
    assert sent.params["query"] == [
        "p95:trace.http.request.duration{service:checkout}.rollup(max, 86400)"
    ]
    assert sent.params["from"] == ["1782864000"] and sent.params["to"] == ["1788220799"]
    assert sent.headers["Dd-api-key"] == "k"
    last = datadog.read({**request, "reduce": "last"}, JUL_AUG, where, wire(web))
    assert last.table is not None and last.table["last"] == [220.0, 300.0]


def test_datadog_refuses_two_series_a_rollup_and_a_foreign_site() -> None:
    web = FakeWeb().on("GET", "/api/v1/query", Reply(fixture("datadog/query_two_series.json")))
    where = _reach("datadog", {"DD_API_KEY": "k", "DD_APP_KEY": "a"})
    with pytest.raises(SourceError, match="2 series"):
        datadog.read({"metric": "avg:x{*} by {service}"}, Q3, where, wire(web))
    with pytest.raises(RequestError, match="rollup"):
        datadog.read({"metric": "avg:x{*}.rollup(sum, 60)"}, Q3, where, wire())
    with pytest.raises(ReachError, match="not a Datadog site"):
        datadog.read(
            {"metric": "avg:x{*}"},
            Q3,
            _reach("datadog", {"DD_API_KEY": "k", "DD_APP_KEY": "a", "DD_SITE": "evil.example"}),
            wire(),
        )


def test_datadog_slo_history_and_rum_totals_per_period() -> None:
    web = FakeWeb()
    web.on("GET", "/api/v1/slo/abc123/history", Reply(fixture("datadog/slo_history.json")))
    web.on("POST", "/api/v2/rum/analytics/aggregate", Reply(fixture("datadog/rum_total.json")))
    where = _reach("datadog", {"DD_API_KEY": "k", "DD_APP_KEY": "a"})
    slo = datadog.read({"slo": "abc123", "per": "month"}, JUL_AUG, where, wire(web))
    assert slo.table == {"month": ["2026-07", "2026-08"], "sli": [99.93, 99.93]}
    rum = {"rum": "@type:view @view.name:/checkout", "measure": "@view.loading_time"}
    result = datadog.read(rum, Q3, where, wire(web))
    assert result.value == 2140.5
    body = web.sent[-1].body
    assert body["compute"] == [
        {"aggregation": "pc75", "type": "total", "metric": "@view.loading_time"}
    ]
    assert body["filter"]["from"] == "2026-07-01T00:00:00Z"
    assert body["filter"]["to"] == "2026-10-01T00:00:00Z"


def test_pagerduty_counts_incidents_and_splits_long_windows_by_month() -> None:
    web = FakeWeb().on("GET", "/incidents", Reply(fixture("pagerduty/incidents_total.json")))
    where = _reach("pagerduty", {"PAGERDUTY_TOKEN": "pd"})
    request = {"incidents": {"urgencies": ["high"], "service_ids": ["P1ABC"]}}
    assert pagerduty.read(request, Q3, where, wire(web)).value == 9
    sent = web.sent[0]
    assert sent.params["urgencies[]"] == ["high"] and sent.params["total"] == ["true"]
    assert sent.headers["Authorization"] == "Token token=pd"
    year = Window(date(2026, 1, 1), date(2026, 12, 31))
    assert pagerduty.read(request, year, where, wire(web)).value == 9 * 12
    with pytest.raises(RequestError, match="unknown"):
        pagerduty.read({"incidents": {"assignee": ["x"]}}, Q3, where, wire())


def test_servicenow_counts_and_averages_through_the_aggregate_api() -> None:
    web = FakeWeb()
    web.on(
        "GET",
        "/api/now/stats/incident",
        Reply(fixture("servicenow/stats_count.json")),
        where={"sysparm_count": "true"},
    )
    where = _reach(
        "servicenow",
        {"SERVICENOW_INSTANCE": "acme", "SERVICENOW_USER": "u", "SERVICENOW_PASSWORD": "p"},
    )
    result = servicenow.read({"table": "incident", "query": "priority=1"}, Q3, where, wire(web))
    assert result.value == 42
    assert web.sent[0].params["sysparm_query"] == [
        "priority=1^opened_atBETWEENjavascript:gs.dateGenerate('2026-07-01','00:00:00')"
        "@javascript:gs.dateGenerate('2026-09-30','23:59:59')"
    ]
    web = FakeWeb().on(
        "GET", "/api/now/stats/incident", Reply(fixture("servicenow/stats_avg.json"))
    )
    token = _reach(
        "servicenow",
        {"SERVICENOW_INSTANCE": "https://acme.service-now.com", "SERVICENOW_TOKEN": "b"},
    )
    average = servicenow.read({"table": "incident", "avg": "calendar_stc"}, Q3, token, wire(web))
    assert average.value == 5400.5
    assert web.sent[0].headers["Authorization"] == "Bearer b"


def test_databricks_runs_a_guarded_statement_and_reads_every_chunk() -> None:
    web = FakeWeb()
    web.on("POST", "/api/2.0/sql/statements", Reply(fixture("databricks/statement_ok.json")))
    web.on(
        "GET",
        "/api/2.0/sql/statements/01ef8b2c/result/chunks/1",
        Reply(fixture("databricks/statement_chunk1.json")),
    )
    where = _reach(
        "databricks", {"DATABRICKS_HOST": "adb-1.azuredatabricks.net", "DATABRICKS_TOKEN": "dapi"}
    )
    request = {
        "sql": "SELECT month, orders, revenue, first_day FROM gold.monthly\n"
        "WHERE day >= :start AND region = :region",
        "params": {"region": "EU"},
        "warehouse": "abc123def4567890",
    }
    result = databricks.read(request, Q3, where, wire(web))
    assert result.table == {
        "month": ["2026-07", "2026-08", "2026-09"],
        "orders": [905, 905, 875],
        "revenue": [44964.95, 43808.95, 42842.25],
        "first_day": ["2026-07-01", "2026-08-01", None],
    }
    body = web.sent[0].body
    assert body["statement"] == (
        "SELECT month, orders, revenue, first_day FROM gold.monthly "
        "WHERE day >= :start AND region = :region"
    )
    assert body["parameters"] == [
        {"name": "start", "value": "2026-07-01", "type": "DATE"},
        {"name": "region", "value": "EU"},
    ]
    assert (body["wait_timeout"], body["on_wait_timeout"], body["row_limit"]) == (
        "30s",
        "CANCEL",
        10001,
    )


def test_databricks_reports_failures_truncation_and_refused_statements() -> None:
    where = _reach(
        "databricks", {"DATABRICKS_HOST": "h.cloud.databricks.com", "DATABRICKS_TOKEN": "d"}
    )
    request = {"sql": "SELECT count(*) FROM ordrs", "warehouse": "abc123def4567890"}
    web = FakeWeb().on(
        "POST", "/api/2.0/sql/statements", Reply(fixture("databricks/statement_failed.json"))
    )
    with pytest.raises(SourceError, match="TABLE_OR_VIEW_NOT_FOUND"):
        databricks.read(request, Q3, where, wire(web))
    web = FakeWeb().on(
        "POST", "/api/2.0/sql/statements", Reply(fixture("databricks/statement_truncated.json"))
    )
    with pytest.raises(SqlError, match="10,000"):
        databricks.read(request, Q3, where, wire(web))
    web = FakeWeb()
    with pytest.raises(SqlError, match="one statement"):
        databricks.read({**request, "sql": "SELECT 1; DROP TABLE x"}, Q3, where, wire(web))
    assert web.sent == []
    one = FakeWeb().on(
        "POST", "/api/2.0/sql/statements", Reply(fixture("databricks/statement_one.json"))
    )
    assert databricks.read(request, Q3, where, wire(one)).value == 2685


def test_databricks_lineage_lists_upstream_and_downstream_tables() -> None:
    web = FakeWeb().on(
        "GET", "/api/2.0/lineage-tracking/table-lineage", Reply(fixture("databricks/lineage.json"))
    )
    where = _reach(
        "databricks", {"DATABRICKS_HOST": "h.cloud.databricks.com", "DATABRICKS_TOKEN": "d"}
    )
    result = databricks.read({"lineage": "main.silver.orders"}, Q3, where, wire(web))
    assert result.table == {
        "upstream": ["main.bronze.raw_orders", "main.bronze.raw_payments"],
        "downstream": ["main.gold.daily_revenue"],
    }


def test_the_transport_refuses_unlisted_posts_plain_http_and_bad_keys() -> None:
    web = FakeWeb().on("GET", "/x", Reply({"message": "nope"}, status=401))
    transport = JsonTransport("Jira", "https://jira.example", {}, opener=web, sleeper=web.sleep)
    with pytest.raises(SourceError, match="refusing POST /issue"):
        transport.post_query("/issue", {})
    with pytest.raises(SourceError, match="non-https"):
        JsonTransport("Jira", "http://jira.example", {}).get("/x")
    with pytest.raises(AuthError, match="HTTP 401"):
        transport.get("/x")
    assert [s.path for s in web.sent] == ["/x"]


def test_the_transport_retries_server_errors_then_gives_up() -> None:
    web = FakeWeb().on("GET", "/x", Reply({}, status=503), Reply({}, status=503), Reply({"ok": 1}))
    transport = JsonTransport("PagerDuty", "https://api.example", {}, opener=web, sleeper=web.sleep)
    assert transport.get("/x") == {"ok": 1}
    assert web.sleeps == [2.0, 4.0]
