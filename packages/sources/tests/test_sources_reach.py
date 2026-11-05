"""Where a collector reads: named connections, default variables and what errors name."""

from __future__ import annotations

import pytest
from sources.core import connections
from sources.core.reach import ReachError, reach


def test_defaults_come_from_the_system_variables() -> None:
    where = reach("datadog", "datadog", {}, {"DD_API_KEY": "k", "DD_APPLICATION_KEY": "a"})
    assert where.need("api_key", "app_key") == ["k", "a"]
    assert where.key("site") == ""


def test_a_named_connection_sets_the_host_and_its_own_variables() -> None:
    named = {
        "eu": connections.connection(
            "eu",
            {
                "system": "jira",
                "host": "https://acme-eu.atlassian.net",
                "env": {"token": "EU_JIRA_TOKEN"},
            },
        )
    }
    environ = {"EU_JIRA_TOKEN": "eu-secret", "JIRA_API_TOKEN": "default", "JIRA_EMAIL": "a@b.c"}
    where = reach("jira", "eu", named, environ)
    assert where.url() == "https://acme-eu.atlassian.net"
    assert where.need("email", "token") == ["a@b.c", "eu-secret"]


def test_errors_name_variables_and_never_their_values() -> None:
    where = reach("jira", "jira", {}, {"JIRA_URL": "https://x.atlassian.net", "JIRA_EMAIL": "me@x"})
    with pytest.raises(ReachError) as caught:
        where.need("email", "token")
    assert str(caught.value) == "jira (jira) needs JIRA_API_TOKEN set"
    assert "me@x" not in str(caught.value)
    with pytest.raises(ReachError, match="not in connections.json"):
        reach("jira", "claude_ai_Atlassian", {}, {})
    named = {"db": connections.connection("db", {"system": "postgres", "host": "db"})}
    with pytest.raises(ReachError, match="reads postgres, not oracle"):
        reach("oracle", "db", named, {})
    with pytest.raises(ReachError, match="https"):
        reach("jira", "jira", {}, {"JIRA_URL": "http://jira.local"}).url()
