"""Small facts and queries files for the sources tests."""

from __future__ import annotations

from typing import Any

TODAY = "2026-10-31"


def facts() -> dict[str, Any]:
    return {
        "github": {
            "merged": {"value": 1240, "source": "github", "note": "merged PRs, Q3 2026"},
            "weekly": {"x": ["2026-07-06", "2026-07-13", "2026-07-20"], "merged": [81, 63, 102]},
        },
        "jira": {"epics_done": {"value": 9, "unit": "epics", "source": "jira"}},
        "derive": {"github.merged_last": {"fn": "last", "of": "github.weekly.merged"}},
    }


def queries() -> dict[str, Any]:
    entry = {
        "lane": "mcp",
        "window": {"start": "2026-07-01", "end": "2026-09-30"},
        "as_of": TODAY,
    }
    return {
        "schema_version": 1,
        "queries": {
            "github": {
                **entry,
                "system": "github",
                "connection": "github",
                "query": 'search_issues q="is:pr is:merged merged:2026-07-01..2026-09-30"',
            },
            "jira.epics_done": {
                **entry,
                "system": "jira",
                "connection": "claude_ai_Atlassian",
                "query": "JQL project = SHOP AND issuetype = Epic AND statusCategory = Done",
            },
        },
    }
