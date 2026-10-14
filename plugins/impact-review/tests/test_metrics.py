from datetime import UTC, datetime

import pytest
from conftest import TIMEFRAME, FakeGitHub, transport_for
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.models import Activity, PullRequest, Review
from impact_review.core.report import build_metrics
from impact_review.core.themes import classify

GENERATED = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


@pytest.fixture
def metrics(github: FakeGitHub) -> dict:
    source = GitHubSource(transport_for(github))
    profile = source.profile()
    activity = source.collect(TIMEFRAME, profile, orgs=[], repo_share=True)
    return build_metrics(profile, TIMEFRAME, activity, "github.com", GENERATED)


def test_header_fields(metrics: dict) -> None:
    assert metrics["schema_version"] == 1
    assert metrics["generated_at"] == "2026-10-11T12:00:00+00:00"
    assert metrics["profile"] == {"login": "jdean", "name": "Jacqueline Dean"}
    assert metrics["timeframe"] == {
        "since": "2026-01-01",
        "until": "2026-09-30",
        "label": "ytd",
        "days": 273,
    }


def test_volume(metrics: dict) -> None:
    v = metrics["volume"]
    assert (v["commits"], v["commits_reported_by_github"]) == (7, 7)
    assert (v["prs_opened"], v["prs_merged"], v["prs_closed_unmerged"], v["prs_open"]) == (
        4,
        2,
        1,
        1,
    )
    assert (
        v["reviews"],
        v["reviews_approved"],
        v["reviews_changes_requested"],
        v["reviews_commented"],
    ) == (3, 1, 1, 1)
    assert v["review_comments"] == 8
    assert v["issues_opened"] == 1
    assert (v["repos_touched"], v["orgs_touched"]) == (3, 2)
    assert v["languages"] == {"Python": 1, "TypeScript": 1, "Go": 1}
    assert v["restricted_contributions"] == 2


def test_code(metrics: dict) -> None:
    c = metrics["code"]
    assert (c["lines_added"], c["lines_deleted"], c["lines_changed"], c["files_changed"]) == (
        432,
        39,
        471,
        8,
    )
    assert c["median_pr_lines"] == 236
    assert c["size_bands"] == {
        "under_10": 0,
        "10_to_99": 1,
        "100_to_499": 1,
        "500_to_999": 0,
        "1000_plus": 0,
    }
    assert (c["commit_lines_added"], c["commit_lines_deleted"]) == (640, 59)


def test_flow_ignores_self_reviews(metrics: dict) -> None:
    f = metrics["flow"]
    assert f["merge_hours_median"] == 27.0
    assert f["merge_hours_p75"] == 48.0
    assert f["first_review_hours_median"] == 6.0
    assert f["prs_with_review"] == 3
    assert f["weeks"] == 39.0
    assert f["prs_merged_per_week"] == 0.05


def test_collaboration(metrics: dict) -> None:
    col = metrics["collaboration"]
    assert col == {
        "authors_reviewed": 3,
        "reviewers_of_own_prs": 3,
        "reviews_per_pr_opened": 0.75,
        "repos_reviewed_in": 2,
        "repos_reviewed_only": 0,
        "cross_repo_reach": 3,
    }


def test_consistency_only_counts_days_inside_the_timeframe(metrics: dict) -> None:
    c = metrics["consistency"]
    assert c["contributions"] == 16
    assert (c["active_days"], c["days_in_timeframe"]) == (9, 273)
    assert c["longest_streak_days"] == 3
    assert (c["active_weeks"], c["weeks_in_timeframe"]) == (7, 40)
    assert c["active_weeks_share"] == round(7 / 40, 2)
    assert c["by_month"]["2026-02"] == 6
    assert "2025-12" not in c["by_month"]
    assert sum(c["by_weekday"].values()) == 16
    assert c["by_weekday"]["Tue"] >= 3


def test_themes(metrics: dict) -> None:
    t = metrics["themes"]
    assert t["feature"] == {"prs": 1, "prs_merged": 1, "lines": 455}
    assert t["fix"] == {"prs": 1, "prs_merged": 1, "lines": 16}
    assert t["refactor"] == {"prs": 1, "prs_merged": 0, "lines": 1600}
    assert t["dependencies"] == {"prs": 1, "prs_merged": 0, "lines": 2900}
    assert t["other"]["prs"] == 0


def test_highlights_rank_prs_and_repos(metrics: dict) -> None:
    top = metrics["highlights"]["top_prs"]
    assert [pr["number"] for pr in top] == [101, 60, 57, 118]
    assert top[0]["reviewers"] == 2
    assert top[0]["score"] > top[1]["score"] > top[2]["score"] > top[3]["score"]
    assert top[0]["merged_at"] == "2026-02-05"
    assert top[0]["url"] == "https://github.com/acme/api/pull/101"
    repos = metrics["highlights"]["top_repos"]
    assert [r["repo"] for r in repos] == ["acme/api", "acme/web", "partners/sdk"]
    assert repos[0] == {
        "repo": "acme/api",
        "commits": 3,
        "prs": 2,
        "prs_merged": 2,
        "reviews": 2,
        "lines": 471,
        "activity": 7,
    }


def test_repo_share_and_warnings(metrics: dict) -> None:
    share = metrics["repo_share"]["acme/api"]
    assert share == {
        "commits": 3,
        "commits_total": 10,
        "commit_share": 0.3,
        "lines": 471,
        "lines_total": 691,
        "line_share": 0.68,
    }
    assert list(metrics["repo_share"]) == ["acme/api", "acme/web"]
    assert any("partners/sdk" in w for w in metrics["warnings"])
    assert len(metrics["limits"]) == 2


def _pr(title: str, labels: tuple[str, ...] = ()) -> PullRequest:
    return PullRequest(
        repo="acme/api",
        owner="acme",
        number=1,
        title=title,
        url="u",
        state="MERGED",
        is_draft=False,
        created_at=GENERATED,
        merged_at=GENERATED,
        closed_at=None,
        additions=1,
        deletions=1,
        changed_files=1,
        labels=labels,
        reviews=(),
        comments=0,
        language=None,
        is_private=False,
    )


@pytest.mark.parametrize(
    ("title", "labels", "theme"),
    [
        ("Anything", ("security",), "security"),
        ("Anything", ("kind/bug",), "fix"),
        ("feat(api): new endpoint", (), "feature"),
        ("[docs] fix typo", (), "docs"),
        ("perf!: faster parser", (), "performance"),
        ("chore(deps): bump urllib3", (), "dependencies"),
        ("chore: tidy", (), "other"),
        ("Bump actions/checkout from 3 to 4", (), "dependencies"),
        ("Fix crash on empty input", (), "fix"),
        ("Add terraform module for VPC", (), "ci_infra"),
        ("Simplify retry loop", (), "refactor"),
        ("Implement SSO login", (), "feature"),
        ("Patch CVE-2026-1234 in parser", (), "security"),
        ("Weekly sync", (), "other"),
    ],
)
def test_classify(title: str, labels: tuple[str, ...], theme: str) -> None:
    assert classify(_pr(title, labels)) == theme


def test_empty_activity_produces_zeroes_not_errors() -> None:
    from impact_review.core.models import Profile

    metrics = build_metrics(Profile("x", "", "id"), TIMEFRAME, Activity(), "github.com", GENERATED)
    assert metrics["volume"]["prs_opened"] == 0
    assert metrics["flow"]["merge_hours_median"] is None
    assert metrics["code"]["median_pr_lines"] is None
    assert metrics["consistency"]["active_days"] == 0
    assert metrics["highlights"] == {"top_prs": [], "top_repos": []}


def test_reviews_on_own_pr_by_self_do_not_count_as_reviewers() -> None:
    from impact_review.core.metrics import collaboration_metrics

    pr = _pr("x")
    own = PullRequest(**{**pr.__dict__, "reviews": (Review("JDean", "COMMENTED", GENERATED),)})
    activity = Activity(pull_requests=[own])
    assert collaboration_metrics(activity, "jdean")["reviewers_of_own_prs"] == 0
