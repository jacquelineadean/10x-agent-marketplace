"""Volume, code, flow and collaboration metrics. Every value here feeds metrics.json."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import datetime
from typing import Any

from impact_review.core.models import Activity, Profile, PullRequest, Timeframe
from impact_review.core.stats import median, percentile, ratio, rounded
from impact_review.core.timeframe import week_count

SIZE_BANDS = (
    ("under_10", 0, 9),
    ("10_to_99", 10, 99),
    ("100_to_499", 100, 499),
    ("500_to_999", 500, 999),
    ("1000_plus", 1000, None),
)


def size_band(lines: int) -> str:
    for name, low, high in SIZE_BANDS:
        if lines >= low and (high is None or lines <= high):
            return name
    return SIZE_BANDS[-1][0]


def repos_touched(activity: Activity) -> set[str]:
    names = {pr.repo for pr in activity.pull_requests}
    names.update(review.repo for review in activity.reviews)
    names.update(commit.repo for commit in activity.commits)
    names.update(issue.repo for issue in activity.issues)
    return names


def volume_metrics(activity: Activity) -> dict[str, Any]:
    prs = activity.pull_requests
    review_states = Counter(review.state for review in activity.reviews)
    languages = Counter(repo.language or "unknown" for repo in activity.repositories)
    return {
        "commits": len(activity.commits),
        "commits_reported_by_github": activity.totals.commits,
        "prs_opened": len(prs),
        "prs_merged": sum(1 for pr in prs if pr.state == "MERGED"),
        "prs_closed_unmerged": sum(1 for pr in prs if pr.state == "CLOSED"),
        "prs_open": sum(1 for pr in prs if pr.state == "OPEN"),
        "reviews": len(activity.reviews),
        "reviews_approved": review_states.get("APPROVED", 0),
        "reviews_changes_requested": review_states.get("CHANGES_REQUESTED", 0),
        "reviews_commented": review_states.get("COMMENTED", 0),
        "reviews_dismissed": review_states.get("DISMISSED", 0),
        "review_comments": sum(review.comments for review in activity.reviews),
        "issues_opened": len(activity.issues),
        "repos_touched": len(repos_touched(activity)),
        "orgs_touched": len({name.split("/")[0] for name in repos_touched(activity)}),
        "languages": dict(languages.most_common()),
        "restricted_contributions": activity.totals.restricted,
    }


def code_metrics(activity: Activity) -> dict[str, Any]:
    merged = [pr for pr in activity.pull_requests if pr.state == "MERGED"]
    bands = Counter(size_band(pr.lines) for pr in merged)
    return {
        "lines_added": sum(pr.additions for pr in merged),
        "lines_deleted": sum(pr.deletions for pr in merged),
        "lines_changed": sum(pr.lines for pr in merged),
        "files_changed": sum(pr.changed_files for pr in merged),
        "median_pr_lines": None
        if (mid := median([pr.lines for pr in merged])) is None
        else round(mid),
        "size_bands": {name: bands.get(name, 0) for name, _, _ in SIZE_BANDS},
        "commit_lines_added": sum(commit.additions for commit in activity.commits),
        "commit_lines_deleted": sum(commit.deletions for commit in activity.commits),
    }


def hours_between(start: datetime, end: datetime) -> float:
    return (end - start).total_seconds() / 3600


def _author_of(pr: PullRequest, fallback: str) -> str:
    return (pr.author or fallback).lower()


def first_review_hours(pr: PullRequest, login: str = "") -> float | None:
    """Hours from opening to the first review by someone other than the PR's author."""
    author = _author_of(pr, login)
    others = [
        review.submitted_at
        for review in pr.reviews
        if review.submitted_at is not None and review.author.lower() != author
    ]
    return hours_between(pr.created_at, min(others)) if others else None


def flow_metrics(activity: Activity, timeframe: Timeframe, people: int = 1) -> dict[str, Any]:
    merged = [pr for pr in activity.pull_requests if pr.state == "MERGED" and pr.merged_at]
    merge_hours = [hours_between(pr.created_at, pr.merged_at) for pr in merged if pr.merged_at]
    review_hours = [
        hours for pr in activity.pull_requests if (hours := first_review_hours(pr)) is not None
    ]
    weeks = week_count(timeframe)
    per_week = len(merged) / weeks if weeks else 0.0
    return {
        "merge_hours_median": rounded(median(merge_hours)),
        "merge_hours_p75": rounded(percentile(merge_hours, 0.75)),
        "first_review_hours_median": rounded(median(review_hours)),
        "prs_with_review": len(review_hours),
        "prs_merged_per_week": round(per_week, 2),
        "prs_merged_per_person_per_week": round(per_week / people, 2) if people else 0.0,
        "weeks": round(weeks, 1),
    }


def collaboration_metrics(activity: Activity, logins: Iterable[str]) -> dict[str, Any]:
    """Self-reviews never count. `logins` are the people in scope, case-insensitive."""
    scope = {login.lower() for login in logins}
    fallback = next(iter(scope)) if len(scope) == 1 else ""
    given = [r for r in activity.reviews if r.pr_author.lower() != (r.reviewer or fallback).lower()]
    authors_reviewed = {r.pr_author.lower() for r in given}
    reviewers = {
        review.author.lower()
        for pr in activity.pull_requests
        for review in pr.reviews
        if review.author.lower() != _author_of(pr, fallback)
    }
    own_repos = {pr.repo for pr in activity.pull_requests} | {c.repo for c in activity.commits}
    review_repos = {review.repo for review in activity.reviews}
    inside = sum(1 for r in given if r.pr_author.lower() in scope)
    return {
        "authors_reviewed": len(authors_reviewed),
        "authors_reviewed_outside_scope": len(authors_reviewed - scope),
        "reviewers_of_own_prs": len(reviewers),
        "reviewers_outside_scope": len(reviewers - scope),
        "reviews_per_pr_opened": ratio(len(activity.reviews), len(activity.pull_requests)),
        "reviews_inside_scope": inside,
        "reviews_outside_scope": len(given) - inside,
        "repos_reviewed_in": len(review_repos),
        "repos_reviewed_only": len(review_repos - own_repos),
        "cross_repo_reach": len(own_repos | review_repos),
    }


def people_metrics(activity: Activity, people: Sequence[Profile]) -> dict[str, Any]:
    """One row per person in scope, keyed by login, most active first."""
    rows: dict[str, dict[str, Any]] = {}
    for person in people:
        key = person.login.lower()
        prs = [pr for pr in activity.pull_requests if pr.author.lower() == key]
        merged = [pr for pr in prs if pr.state == "MERGED"]
        calendar = activity.calendars.get(key, {})
        rows[person.login] = {
            "name": person.name,
            "commits": sum(1 for c in activity.commits if c.author.lower() == key),
            "prs_opened": len(prs),
            "prs_merged": len(merged),
            "reviews": sum(1 for r in activity.reviews if r.reviewer.lower() == key),
            "issues_opened": sum(1 for i in activity.issues if i.author.lower() == key),
            "lines_changed": sum(pr.lines for pr in merged),
            "active_days": sum(1 for count in calendar.values() if count > 0),
        }
    ranked = sorted(
        rows.items(),
        key=lambda item: (
            item[1]["prs_merged"] + item[1]["reviews"] + item[1]["commits"],
            item[0].lower(),
        ),
        reverse=True,
    )
    return dict(ranked)
