from datetime import date
from pathlib import Path

import pytest
from conftest import (
    TIMEFRAME,
    FakeGitHub,
    Reply,
    fixture,
    me_scope,
    recorded_github,
    solo,
    transport_for,
)
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.models import Timeframe


def test_profile_comes_from_viewer(source: GitHubSource) -> None:
    profile = source.profile()
    assert (profile.login, profile.name, profile.node_id) == (
        "srivera",
        "Sam Rivera",
        "MDQ6VXNlcjE=",
    )
    assert profile.created_at == date(2019, 4, 2)


def test_collect_gathers_every_contribution_kind(source: GitHubSource, github: FakeGitHub) -> None:
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=False)
    assert [pr.number for pr in activity.pull_requests] == [101, 118, 57, 60]
    assert [r.pr_number for r in activity.reviews] == [130, 131, 9]
    assert [i.number for i in activity.issues] == [140]
    assert sorted(c.oid for c in activity.commits) == ["a1", "a2", "a3", "s1", "s2", "w1", "w2"]
    assert activity.totals.commits == 7
    assert activity.totals.restricted == 2
    assert activity.calendar[date(2026, 3, 10)] == 4
    assert [r.name for r in activity.repositories] == ["acme/api", "acme/web", "partners/sdk"]
    assert activity.repo_shares == []
    assert len(github.calls("PullRequests")) == 2
    assert github.calls("PullRequests")[1].variables["after"] == "cursor-1"
    assert github.calls("Contributions")[0].variables == {
        "login": "srivera",
        "from": "2026-01-01T00:00:00Z",
        "to": "2026-09-30T23:59:59Z",
    }


def test_commits_use_the_viewer_node_id_and_whole_timeframe(
    source: GitHubSource, github: FakeGitHub
) -> None:
    source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=False)
    first = github.calls("Commits")[0].variables
    assert first["author"] == "MDQ6VXNlcjE="
    assert (first["since"], first["until"]) == ("2026-01-01T00:00:00Z", "2026-09-30T23:59:59Z")
    assert (first["owner"], first["name"]) == ("acme", "api")


def test_org_filter_drops_other_owners_before_fetching_commits(
    source: GitHubSource, github: FakeGitHub
) -> None:
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=["ACME"], repo_share=False)
    assert {pr.owner for pr in activity.pull_requests} == {"acme"}
    assert [r.pr_number for r in activity.reviews] == [130, 131]
    assert [r.name for r in activity.repositories] == ["acme/api", "acme/web"]
    assert {c.repo for c in activity.commits} == {"acme/api", "acme/web"}
    assert all(c.variables["owner"] == "acme" for c in github.calls("Commits"))


def test_repo_share_retries_202_three_times_then_warns(
    source: GitHubSource, github: FakeGitHub
) -> None:
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=True)
    shares = {s.repo: s for s in activity.repo_shares}
    assert shares["acme/api"].commits == 3
    assert shares["acme/api"].commits_total == 10
    assert (shares["acme/api"].lines, shares["acme/api"].lines_total) == (471, 691)
    assert "partners/sdk" not in shares
    assert any("partners/sdk" in w and "3 attempts" in w for w in activity.warnings)
    stats_calls = [
        s for s in github.sent if s.operation and s.operation.endswith("stats/contributors")
    ]
    assert len(stats_calls) == 2 + 1 + 3
    assert github.sleeps == [2.0, 2.0, 4.0]


def test_cache_makes_a_rerun_free_and_refresh_bypasses_it(tmp_path: Path) -> None:
    github = recorded_github()
    source = GitHubSource(transport_for(github))
    source.enable_cache(tmp_path / "raw", refresh=False)
    profile = source.profile()
    first = source.collect(TIMEFRAME, solo(profile), orgs=[], repo_share=True)
    calls_after_first = len(github.sent)
    files = sorted(p.name for p in (tmp_path / "raw").iterdir())
    assert any(name.startswith("pull_requests-") for name in files)
    assert any(name.startswith("stats_contributors-") for name in files)
    assert len(files) == 1 + 2 + 1 + 1 + 3 + 2

    again = GitHubSource(transport_for(github))
    again.enable_cache(tmp_path / "raw", refresh=False)
    second = again.collect(TIMEFRAME, solo(profile), orgs=[], repo_share=True)
    retried = github.sent[calls_after_first:]
    assert all(s.operation == "repos/partners/sdk/stats/contributors" for s in retried)
    assert len(retried) == 3
    assert second.pull_requests == first.pull_requests
    assert second.repo_shares == first.repo_shares

    fresh = GitHubSource(transport_for(github))
    fresh.enable_cache(tmp_path / "raw", refresh=True)
    before_refresh = len(github.sent)
    fresh.collect(TIMEFRAME, solo(profile), orgs=[], repo_share=False)
    assert len(github.sent) == before_refresh + calls_after_first - 1 - 2 - 1 - 3


def test_raw_cache_never_contains_the_token(tmp_path: Path) -> None:
    from conftest import TOKEN

    github = recorded_github()
    source = GitHubSource(transport_for(github))
    source.enable_cache(tmp_path / "raw", refresh=False)
    source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=True)
    for path in (tmp_path / "raw").iterdir():
        assert TOKEN not in path.read_text()


def test_ranges_over_a_year_query_each_chunk_and_dedupe(github: FakeGitHub) -> None:
    source = GitHubSource(transport_for(github))
    frame = Timeframe(date(2025, 6, 1), date(2026, 9, 30), "custom")
    activity = source.collect(frame, me_scope(source), orgs=[], repo_share=False)
    assert len(github.calls("Contributions")) == 2
    assert [pr.number for pr in activity.pull_requests] == [101, 118, 57, 60]
    assert [r.name for r in activity.repositories] == ["acme/api", "acme/web", "partners/sdk"]
    assert activity.totals.commits == 14
    assert activity.calendar[date(2026, 3, 10)] == 8


def test_partial_graphql_errors_become_warnings(github: FakeGitHub) -> None:
    github.replies["Commits:partners/sdk"] = [Reply(body=fixture("partial_error"))]
    source = GitHubSource(transport_for(github))
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=False)
    assert any("partial data for commits" in w for w in activity.warnings)
    assert any(c.oid == "p1" and c.changed_files == 0 for c in activity.commits)


def test_repo_without_default_branch_is_skipped_with_warning(github: FakeGitHub) -> None:
    body = fixture("contributions")
    repos = body["data"]["user"]["contributionsCollection"]["commitContributionsByRepository"]
    repos[2]["repository"]["defaultBranchRef"] = None
    github.replies["Contributions"] = [Reply(body=body)]
    source = GitHubSource(transport_for(github))
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=False)
    assert not any(c.repo == "partners/sdk" for c in activity.commits)
    assert any("partners/sdk has no default branch" in w for w in activity.warnings)


@pytest.mark.parametrize("empty_key", ["pullRequest", "pullRequestReview", "issue"])
def test_null_nodes_are_ignored(github: FakeGitHub, empty_key: str) -> None:
    name = {
        "pullRequest": "pull_requests_page2",
        "pullRequestReview": "reviews_page1",
        "issue": "issues_page1",
    }[empty_key]
    body = fixture(name)
    collection = body["data"]["user"]["contributionsCollection"]
    connection = next(iter(collection.values()))
    connection["nodes"].append({empty_key: None})
    connection["nodes"].append(None)
    key = {
        "pull_requests_page2": "PullRequests@cursor-1",
        "reviews_page1": "Reviews",
        "issues_page1": "Issues",
    }[name]
    github.replies[key] = [Reply(body=body)]
    source = GitHubSource(transport_for(github))
    activity = source.collect(TIMEFRAME, me_scope(source), orgs=[], repo_share=False)
    assert len(activity.pull_requests) == 4
    assert len(activity.reviews) == 3
    assert len(activity.issues) == 1
