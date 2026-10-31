"""The nine systems the gatherer reads, grouped as the source picker asks about them."""

from __future__ import annotations

from dataclasses import dataclass

# Picker groups in the order the questions appear, with each question's chip label.
GROUPS = {
    "work": ("Code & work", "Which code and work systems should the page draw on?"),
    "operations": ("Operations", "Which operations systems should the page draw on?"),
    "data": ("Data", "Which data platforms should the page draw on?"),
}


@dataclass(frozen=True)
class System:
    """How a system is reached: an MCP connector, keys in the environment or a program.

    `keys` lists alternative sets of environment variable names; any complete set counts.
    `connectors` are words that name the system's MCP server in a session's tool names.
    """

    id: str
    label: str
    group: str
    keys: tuple[tuple[str, ...], ...]
    programs: tuple[str, ...]
    connectors: tuple[str, ...]


SYSTEMS = (
    System("github", "GitHub", "work", (("GITHUB_TOKEN",), ("GH_TOKEN",)), ("gh",), ("github",)),
    System(
        "jira",
        "Jira",
        "work",
        (("JIRA_URL", "JIRA_EMAIL", "JIRA_API_TOKEN"),),
        (),
        ("atlassian", "jira"),
    ),
    System(
        "confluence",
        "Confluence",
        "work",
        (("CONFLUENCE_URL", "CONFLUENCE_EMAIL", "CONFLUENCE_API_TOKEN"),),
        (),
        ("atlassian", "confluence"),
    ),
    System(
        "datadog",
        "Datadog",
        "operations",
        (("DD_API_KEY", "DD_APP_KEY"), ("DD_API_KEY", "DD_APPLICATION_KEY")),
        (),
        ("datadog",),
    ),
    System("pagerduty", "PagerDuty", "operations", (("PAGERDUTY_TOKEN",),), (), ("pagerduty",)),
    System(
        "servicenow",
        "ServiceNow",
        "operations",
        (
            ("SERVICENOW_INSTANCE", "SERVICENOW_USER", "SERVICENOW_PASSWORD"),
            ("SERVICENOW_INSTANCE", "SERVICENOW_TOKEN"),
        ),
        (),
        ("servicenow", "snow"),
    ),
    System(
        "databricks",
        "Databricks",
        "data",
        (("DATABRICKS_HOST", "DATABRICKS_TOKEN"),),
        ("databricks",),
        ("databricks",),
    ),
    System(
        "postgres",
        "Postgres",
        "data",
        (("DATABASE_URL",), ("PGHOST", "PGDATABASE")),
        ("psql",),
        ("postgres", "postgresql", "pg"),
    ),
    System(
        "oracle",
        "Oracle",
        "data",
        (("ORACLE_USER", "ORACLE_PASSWORD", "ORACLE_DSN"),),
        ("sql",),
        ("oracle", "sqlcl"),
    ),
)
BY_ID = {s.id: s for s in SYSTEMS}


def key_names() -> tuple[str, ...]:
    """Every environment variable name any system reads, for a presence check."""
    return tuple(dict.fromkeys(name for s in SYSTEMS for group in s.keys for name in group))


def program_names() -> tuple[str, ...]:
    return tuple(dict.fromkeys(p for s in SYSTEMS for p in s.programs))
