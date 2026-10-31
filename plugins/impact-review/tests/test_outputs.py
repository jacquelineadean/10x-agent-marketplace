from datetime import UTC, datetime

import pytest
from conftest import TIMEFRAME, FakeGitHub, transport_for
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.budget import estimate_budget
from impact_review.core.dashboard import render_dashboard_html, render_dashboard_md
from impact_review.core.digest import DIGEST_CAP_BYTES, render_digest
from impact_review.core.models import Activity, Profile, PullRequest
from impact_review.core.report import build_metrics

GENERATED = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def metrics(github: FakeGitHub) -> dict:
    source = GitHubSource(transport_for(github))
    profile = source.profile()
    activity = source.collect(TIMEFRAME, profile, orgs=[], repo_share=True)
    return build_metrics(profile, TIMEFRAME, activity, "github.com", GENERATED)


def test_digest_labels_every_number_with_its_metrics_key(metrics: dict) -> None:
    digest = render_digest(metrics)
    assert digest.startswith("# Impact digest for Sam Rivera (@srivera)")
    assert "- PRs merged: 2 (volume.prs_merged)" in digest
    assert "- Median hours to merge: 27.0 (flow.merge_hours_median)" in digest
    assert "- acme/api#101 feat: add rate limiter (merged, feature, 455 lines" in digest
    assert "(highlights.top_prs[0])" in digest
    assert "- acme/api: 3 of 10 commits (0.3)" in digest
    assert "## Limits" in digest
    assert "default branches only" in digest
    assert "## Warnings" in digest
    assert len(digest.encode("utf-8")) <= DIGEST_CAP_BYTES


def _huge_activity(count: int) -> Activity:
    prs = [
        PullRequest(
            repo="acme/api",
            owner="acme",
            number=i,
            title="x" * 900,
            url=f"u{i}",
            state="MERGED",
            is_draft=False,
            created_at=GENERATED,
            merged_at=GENERATED,
            closed_at=None,
            additions=i,
            deletions=0,
            changed_files=1,
            labels=(),
            reviews=(),
            comments=i,
            language=None,
            is_private=False,
        )
        for i in range(count)
    ]
    return Activity(pull_requests=prs, warnings=["w" * 300] * 10)


def test_digest_drops_top_pr_rows_to_fit_the_cap() -> None:
    metrics = build_metrics(Profile("x", "", "id"), TIMEFRAME, _huge_activity(15), "h", GENERATED)
    digest = render_digest(metrics)
    assert len(digest.encode("utf-8")) <= DIGEST_CAP_BYTES
    assert digest.count("(highlights.top_prs[") < 15
    assert digest.count("(highlights.top_prs[") >= 3
    assert "## Limits" in digest


def test_digest_truncates_with_a_note_when_rows_alone_cannot_fit() -> None:
    metrics = build_metrics(Profile("x", "", "id"), TIMEFRAME, _huge_activity(15), "h", GENERATED)
    metrics["warnings"] = ["w" * 2000] * 10
    digest = render_digest(metrics, cap_bytes=4_000)
    assert len(digest.encode("utf-8")) <= 4_000
    assert digest.rstrip().endswith("metrics.json holds the full data._")


def test_dashboard_markdown_has_summary_and_tables(metrics: dict) -> None:
    text = render_dashboard_md(metrics)
    assert text.startswith("# Impact dashboard: @srivera 2026-01-01 to 2026-09-30")
    assert "| PRs opened / merged / closed unmerged | 4 / 2 / 1 |" in text
    assert "| acme/api#101 | feat: add rate limiter | merged | feature | 455 | 3 | 3 | 2 |" in text
    assert "## Share of repository work" in text
    assert "| 2026-02 | 6 |" in text


def test_dashboard_html_is_offline_and_escaped(metrics: dict) -> None:
    metrics["highlights"]["top_prs"][0]["title"] = "<b>bold</b> & co"
    html = render_dashboard_html(metrics)
    assert html.startswith("<!DOCTYPE html>")
    assert "<script" not in html
    assert " src=" not in html
    assert " href=" not in html
    assert "<link" not in html
    assert html.count("<svg") == 4
    assert "&lt;b&gt;bold&lt;/b&gt; &amp; co" in html
    assert "<b>bold</b>" not in html
    assert 'aria-label="Contributions by month"' in html


def test_budget_parts_and_cap() -> None:
    budget = estimate_budget(digest_bytes=8_000, instructions_bytes=6_001, cap=25_000)
    assert budget["parts"] == {
        "digest": 2_000,
        "rubric_and_writer_instructions": 1_501,
        "system_overhead": 5_000,
        "output_allowance": 6_000,
        "main_conversation": 3_000,
    }
    assert budget["estimated_tokens"] == 17_501
    assert budget["within_cap"] is True
    over = estimate_budget(digest_bytes=12_000, instructions_bytes=None, cap=18_000)
    assert over["parts"]["digest"] == 3_000
    assert over["parts"]["rubric_and_writer_instructions"] == 2_000
    assert over["estimated_tokens"] == 19_000
    assert over["within_cap"] is False


def test_budget_caps_the_digest_part_at_3000_tokens() -> None:
    assert estimate_budget(50_000, 0, 25_000)["parts"]["digest"] == 3_000
