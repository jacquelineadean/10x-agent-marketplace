"""Group scopes: user lists, teams, organizations and enterprises, end to end on recordings."""

import io
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from conftest import (
    TIMEFRAME,
    TKIM_ID,
    TODAY,
    FakeGitHub,
    Reply,
    fixture,
    team_github,
    transport_for,
)
from impact_review.connectors.github.errors import GitHubError
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.digest import render_digest
from impact_review.core.ports import ActivitySource
from impact_review.core.report import build_metrics
from impact_review.core.scope import Scope, finish_scope, parse_scope
from impact_review.entrypoints.cli.main import run

GENERATED = datetime(2026, 10, 11, 12, 0, tzinfo=UTC)


def _scope(source: GitHubSource, text: str, exclude: tuple[str, ...] = ("lee",)) -> Scope:
    request = parse_scope(text)
    people, orgs = source.resolve(request)
    return finish_scope(request, people, orgs, list(exclude), 100)


def test_user_list_resolves_each_login() -> None:
    github = team_github()
    scope = _scope(GitHubSource(transport_for(github)), "user:srivera,tkim")
    assert [p.login for p in scope.people] == ["srivera", "tkim"]
    assert scope.people[1].created_at == date(2021, 6, 15)
    assert scope.orgs == ()
    assert [s.variables for s in github.calls("User")] == [{"login": "srivera"}, {"login": "tkim"}]


def test_team_scope_lists_members_and_limits_repos_to_the_org() -> None:
    github = team_github()
    scope = _scope(GitHubSource(transport_for(github)), "team:acme/platform", exclude=())
    assert [p.login for p in scope.people] == ["srivera", "tkim", "lee"]
    assert scope.orgs == ("acme",)
    assert github.calls("TeamMembers")[0].variables == {
        "org": "acme",
        "slug": "platform",
        "after": None,
    }


def test_org_scope_follows_member_pages() -> None:
    github = team_github()
    scope = _scope(GitHubSource(transport_for(github)), "org:acme")
    assert [p.login for p in scope.people] == ["srivera", "tkim"]
    assert [c.variables["after"] for c in github.calls("OrgMembers")] == [None, "m-1"]


def test_enterprise_scope_is_the_members_of_its_organizations() -> None:
    github = team_github()
    scope = _scope(GitHubSource(transport_for(github)), "enterprise:acme-corp")
    assert [p.login for p in scope.people] == ["srivera", "tkim"]
    assert scope.orgs == ("acme",)


@pytest.mark.parametrize(
    ("text", "key", "body", "message"),
    [
        ("team:acme/nope", "TeamMembers", "team_missing", "team acme/nope not found"),
        ("user:ghost-user", "", "", "user 'ghost-user' not found"),
        ("org:acme", "OrgMembers", None, "organization acme not found"),
        ("enterprise:acme-corp", "EnterpriseOrgs", None, "lacks read:enterprise"),
    ],
)
def test_missing_scope_targets_name_the_cause(
    text: str, key: str, body: str | None, message: str
) -> None:
    github = team_github()
    if key:
        github.replies[key] = [Reply(body=fixture(body) if body else {"data": {}})]
    with pytest.raises(GitHubError, match=message):
        _scope(GitHubSource(transport_for(github)), text)


@pytest.fixture
def team_activity() -> tuple[Scope, object, FakeGitHub]:
    github = team_github()
    source = GitHubSource(transport_for(github))
    scope = _scope(source, "team:acme/platform")
    return scope, source.collect(TIMEFRAME, scope, list(scope.orgs), repo_share=True), github


def test_group_collect_merges_people_and_dedupes(team_activity) -> None:  # type: ignore[no-untyped-def]
    scope, activity, github = team_activity
    assert {pr.number: pr.author for pr in activity.pull_requests} == {
        101: "srivera",
        118: "srivera",
        57: "srivera",
        60: "srivera",
        150: "tkim",
    }
    assert sorted(c.oid for c in activity.commits) == ["a1", "a2", "a3", "t1", "w1", "w2"]
    assert {r.reviewer for r in activity.reviews} == {"srivera", "tkim"}
    assert activity.calendar[date(2026, 3, 10)] == 6
    assert activity.calendars["tkim"][date(2026, 3, 10)] == 2
    assert [r.name for r in activity.repositories] == ["acme/api", "acme/web"]
    assert github.calls("Contributions")[1].variables["login"] == "tkim"
    assert any(c.variables["author"] == TKIM_ID for c in github.calls("Commits"))
    shares = {s.repo: s for s in activity.repo_shares}
    assert shares["acme/api"].commits == 3


def test_group_metrics_count_people_and_inside_reviews(team_activity) -> None:  # type: ignore[no-untyped-def]
    scope, activity, _ = team_activity
    metrics = build_metrics(scope, TIMEFRAME, activity, "github.com", GENERATED, ["acme"])
    assert metrics["scope"]["label"] == "team acme/platform (2 people)"
    assert metrics["scope"]["individual"] is False
    assert (metrics["volume"]["people"], metrics["volume"]["active_people"]) == (2, 2)
    assert metrics["volume"]["prs_merged"] == 3
    col = metrics["collaboration"]
    assert col["reviews_inside_scope"] == 1
    assert col["reviews_outside_scope"] == 2  # partners/sdk#9 is outside org acme
    assert col["reviewers_outside_scope"] == 3
    assert metrics["flow"]["prs_merged_per_person_per_week"] == round(3 / 39 / 2, 2)
    assert list(metrics["people"]) == ["srivera", "tkim"]
    assert metrics["people"]["tkim"] == {
        "name": "Taylor Kim",
        "commits": 1,
        "prs_opened": 1,
        "prs_merged": 1,
        "reviews": 1,
        "issues_opened": 0,
        "lines_changed": 25,
        "active_days": 2,
    }
    tkim_pr = next(pr for pr in metrics["highlights"]["top_prs"] if pr["number"] == 150)
    assert (tkim_pr["author"], tkim_pr["reviewers"]) == ("tkim", 1)
    digest = render_digest(metrics)
    assert digest.startswith("# Impact digest for team acme/platform (2 people)")
    assert "Scope: group (team), 2 people (scope.people). Repositories: acme." in digest
    assert "- @tkim (Taylor Kim): 1 PRs merged of 1" in digest
    assert "(people.tkim)" in digest
    assert "(volume.active_people)" in digest
    assert "(collaboration.reviews_inside_scope" in digest


def _run(github: FakeGitHub, argv: list[str], env: dict[str, str]) -> tuple[int, str, str]:
    def make_source(host: str) -> ActivitySource:
        return GitHubSource(transport_for(github, host))

    out, err = io.StringIO(), io.StringIO()
    code = run(argv, make_source, env, today=TODAY, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_cli_team_run_uses_the_group_rubric_and_a_team_folder(tmp_path: Path) -> None:
    code, out, err = _run(
        team_github(),
        ["collect", "--scope", "team:acme/platform", "--exclude", "lee", "--timeframe", "2026"],
        {"IMPACT_REVIEW_RUNS": str(tmp_path)},
    )
    assert code == 0, err
    folder = tmp_path / "github.com" / "team-acme-platform" / "2026-01-01_2026-10-11"
    assert f"run folder: {folder}" in out
    assert "scope: team acme/platform (2 people) on github.com" in out
    assert "timeframe: 2026-01-01 to 2026-10-11 (2026, 284 days)" in out
    assert "# Group review rubric" in (folder / "rubric.md").read_text()
    metrics = json.loads((folder / "metrics.json").read_text())
    assert metrics["scope"]["orgs"] == ["acme"]
    assert "## People" in (folder / "dashboard.md").read_text()


def test_cli_org_flag_overrides_the_scope_orgs(tmp_path: Path) -> None:
    code, _, err = _run(
        team_github(),
        ["collect", "--scope", "org:acme", "--org", "partners", "--out", str(tmp_path)],
        {},
    )
    assert code == 0, err
    metrics = json.loads((tmp_path / "metrics.json").read_text())
    assert metrics["scope"]["orgs"] == ["partners"]
    assert {r["repo"] for r in metrics["highlights"]["top_repos"]} == {"partners/sdk"}


def test_cli_all_time_starts_at_the_oldest_account(tmp_path: Path) -> None:
    code, out, err = _run(
        team_github(),
        ["collect", "--scope", "user:tkim", "--timeframe", "all time", "--out", str(tmp_path)],
        {},
    )
    assert code == 0, err
    assert "timeframe: 2021-06-15 to 2026-10-11 (all time, 1945 days)" in out
    assert "scope: Taylor Kim (@tkim)" in out
    assert "# Individual review rubric" in (tmp_path / "rubric.md").read_text()


def test_cli_max_people_stops_before_collecting(tmp_path: Path) -> None:
    github = team_github()
    code, out, err = _run(
        github, ["collect", "--scope", "team:acme/platform", "--max-people", "2"], {}
    )
    assert code == 1
    assert out == ""
    assert "3 people, over --max-people 2" in err
    assert not github.calls("Contributions")


def test_cli_bad_scope_fails_before_any_request() -> None:
    github = team_github()
    code, _, err = _run(github, ["collect", "--scope", "galaxy:x"], {})
    assert code == 1
    assert "unknown scope" in err
    assert github.sent == []
