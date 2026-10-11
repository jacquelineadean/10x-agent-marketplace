"""Turn GraphQL and REST payloads into core records. Missing fields become None or 0."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from impact_review.core.models import (
    Commit,
    Issue,
    Profile,
    PullRequest,
    RepoShare,
    Repository,
    Review,
    ReviewGiven,
    Totals,
)


def parse_datetime(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value.replace("Z", "+00:00")) if value else None


def _required_datetime(value: str | None) -> datetime:
    parsed = parse_datetime(value)
    if parsed is None:
        raise ValueError("GitHub omitted a required timestamp")
    return parsed


def _login(node: dict[str, Any] | None) -> str:
    return str((node or {}).get("login") or "ghost")


def _labels(node: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(label["name"]) for label in (node.get("labels") or {}).get("nodes") or [])


def _repo_name(node: dict[str, Any]) -> tuple[str, str]:
    repository = node.get("repository") or {}
    name = str(repository.get("nameWithOwner") or "unknown/unknown")
    return name, str((repository.get("owner") or {}).get("login") or name.split("/")[0])


def parse_profile(data: dict[str, Any]) -> Profile:
    viewer = data["viewer"]
    return Profile(login=viewer["login"], name=viewer.get("name") or "", node_id=viewer["id"])


def parse_totals(collection: dict[str, Any]) -> Totals:
    return Totals(
        commits=int(collection.get("totalCommitContributions") or 0),
        pull_requests=int(collection.get("totalPullRequestContributions") or 0),
        reviews=int(collection.get("totalPullRequestReviewContributions") or 0),
        issues=int(collection.get("totalIssueContributions") or 0),
        restricted=int(collection.get("restrictedContributionsCount") or 0),
    )


def parse_calendar(collection: dict[str, Any]) -> dict[date, int]:
    days: dict[date, int] = {}
    for week in (collection.get("contributionCalendar") or {}).get("weeks") or []:
        for day in week.get("contributionDays") or []:
            days[date.fromisoformat(day["date"])] = int(day.get("contributionCount") or 0)
    return days


def parse_repositories(collection: dict[str, Any]) -> list[Repository]:
    repos = []
    for entry in collection.get("commitContributionsByRepository") or []:
        node = entry.get("repository") or {}
        name, owner = _repo_name({"repository": node})
        repos.append(
            Repository(
                name=name,
                owner=owner,
                is_private=bool(node.get("isPrivate")),
                language=(node.get("primaryLanguage") or {}).get("name"),
                default_branch=(node.get("defaultBranchRef") or {}).get("name"),
            )
        )
    return repos


def parse_pull_request(node: dict[str, Any]) -> PullRequest:
    name, owner = _repo_name(node)
    repository = node.get("repository") or {}
    reviews = tuple(
        Review(
            author=_login(r.get("author")),
            state=str(r.get("state") or "COMMENTED"),
            submitted_at=parse_datetime(r.get("submittedAt")),
        )
        for r in (node.get("reviews") or {}).get("nodes") or []
    )
    return PullRequest(
        repo=name,
        owner=owner,
        number=int(node["number"]),
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        state=str(node.get("state") or "OPEN"),
        is_draft=bool(node.get("isDraft")),
        created_at=_required_datetime(node.get("createdAt")),
        merged_at=parse_datetime(node.get("mergedAt")),
        closed_at=parse_datetime(node.get("closedAt")),
        additions=int(node.get("additions") or 0),
        deletions=int(node.get("deletions") or 0),
        changed_files=int(node.get("changedFiles") or 0),
        labels=_labels(node),
        reviews=reviews,
        comments=int((node.get("comments") or {}).get("totalCount") or 0),
        language=(repository.get("primaryLanguage") or {}).get("name"),
        is_private=bool(repository.get("isPrivate")),
    )


def parse_review(node: dict[str, Any]) -> ReviewGiven:
    pull_request = node.get("pullRequest") or {}
    name, owner = _repo_name(pull_request)
    return ReviewGiven(
        repo=name,
        owner=owner,
        pr_number=int(pull_request.get("number") or 0),
        pr_title=str(pull_request.get("title") or ""),
        pr_url=str(pull_request.get("url") or ""),
        pr_author=_login(pull_request.get("author")),
        state=str(node.get("state") or "COMMENTED"),
        submitted_at=_required_datetime(node.get("submittedAt")),
        comments=int((node.get("comments") or {}).get("totalCount") or 0),
    )


def parse_issue(node: dict[str, Any]) -> Issue:
    name, owner = _repo_name(node)
    return Issue(
        repo=name,
        owner=owner,
        number=int(node["number"]),
        title=str(node.get("title") or ""),
        url=str(node.get("url") or ""),
        state=str(node.get("state") or "OPEN"),
        created_at=_required_datetime(node.get("createdAt")),
        closed_at=parse_datetime(node.get("closedAt")),
        labels=_labels(node),
    )


def parse_commit(node: dict[str, Any], repo: str, owner: str) -> Commit:
    linked = (node.get("associatedPullRequests") or {}).get("nodes") or []
    return Commit(
        repo=repo,
        owner=owner,
        oid=str(node["oid"]),
        committed_at=_required_datetime(node.get("committedDate")),
        headline=str(node.get("messageHeadline") or ""),
        additions=int(node.get("additions") or 0),
        deletions=int(node.get("deletions") or 0),
        changed_files=int(node.get("changedFilesIfAvailable") or 0),
        pr_number=int(linked[0]["number"]) if linked else None,
    )


def parse_repo_share(repo: str, login: str, since: date, until: date, rows: list[Any]) -> RepoShare:
    """REST stats/contributors rows: weekly buckets per author, summed inside the timeframe."""
    mine_commits = mine_lines = all_commits = all_lines = 0
    for row in rows:
        is_me = _login(row.get("author")).lower() == login.lower()
        for week in row.get("weeks") or []:
            day = datetime.fromtimestamp(int(week.get("w") or 0), UTC).date()
            if not since <= day <= until:
                continue
            commits, lines = (
                int(week.get("c") or 0),
                int(week.get("a") or 0) + int(week.get("d") or 0),
            )
            all_commits += commits
            all_lines += lines
            if is_me:
                mine_commits += commits
                mine_lines += lines
    return RepoShare(
        repo=repo,
        commits=mine_commits,
        commits_total=all_commits,
        lines=mine_lines,
        lines_total=all_lines,
    )
