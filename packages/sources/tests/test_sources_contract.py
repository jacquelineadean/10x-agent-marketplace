"""The facts contract between a gatherer's facts.json and queries.json, and the digest."""

from __future__ import annotations

from datetime import date
from typing import Any

from sources.core import contract, digest
from sources_helpers import TODAY, facts, queries


def _check(f: Any, q: Any) -> contract.Report:
    return contract.check(f, q, date.fromisoformat(TODAY))


def test_a_good_run_folder_passes() -> None:
    report = _check(facts(), queries())
    assert report.errors == [] and report.warnings == []


def test_every_fact_needs_a_query_and_its_system_as_source() -> None:
    f = facts()
    f["jira"]["velocity"] = {"value": 31, "source": "github"}
    report = _check(f, queries())
    assert "jira.velocity: no entry in queries.json names its query" in report.errors
    assert "jira.velocity: source must be 'jira', the system it came from" in report.errors


def test_top_level_keys_are_systems() -> None:
    f = {**facts(), "notes": {"x": {"value": 1, "source": "notes"}}}
    assert any("'notes' is not a system" in e for e in _check(f, queries()).errors)


def test_query_entries_are_checked() -> None:
    q = queries()
    q["queries"]["github"].update(lane="ftp", as_of="2026-11-30", query="")
    q["queries"]["github"]["window"] = {"start": "2026-09-30", "end": "2026-07-01"}
    errors = " ".join(_check(facts(), q).errors)
    for part in ("lane must be", "as_of must be", "query must be", "window needs"):
        assert part in errors


def test_an_orphan_query_is_a_warning() -> None:
    q = queries()
    q["queries"]["jira.velocity"] = dict(q["queries"]["jira.epics_done"])
    assert _check(facts(), q).warnings == [
        "queries.json jira.velocity: names no fact in facts.json"
    ]


def test_digest_lists_facts_series_and_derived_targets() -> None:
    text = digest.render(facts(), queries(), date.fromisoformat(TODAY))
    assert "| `github.merged` | 1240 | merged PRs, Q3 2026 |" in text
    assert "| `jira.epics_done` | 9 epics |  |" in text
    assert "3 points, 81 to 102, range 63 to 102" in text
    assert "Lane mcp through claude_ai_Atlassian; as of 2026-10-31." in text
    assert "| `github.merged_last` | last |" in text


def test_digest_stays_under_its_cap_and_counts_what_it_cut() -> None:
    f = facts()
    f["github"].update(
        {f"repo_{i}": {"value": i, "source": "github", "note": "x" * 60} for i in range(400)}
    )
    text = digest.render(f, queries(), date.fromisoformat(TODAY))
    assert len(text.encode("utf-8")) <= digest.LIMIT
    assert "more facts under `github` are in facts.json." in text
    assert "| `jira.epics_done` |" in text
