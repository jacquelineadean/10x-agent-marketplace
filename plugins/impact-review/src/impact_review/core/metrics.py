"""Volume, code, flow and collaboration metrics. Every value here feeds metrics.json."""

from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any

from impact_review.core.models import Activity, PullRequest, Timeframe
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


def first_review_hours(pr: PullRequest, login: str) -> float | None:
    others = [
        review.submitted_at
        for review in pr.reviews
        if review.submitted_at is not None and review.author.lower() != login.lower()
    ]
    return hours_between(pr.created_at, min(others)) if others else None


def flow_metrics(activity: Activity, timeframe: Timeframe, login: str) -> dict[str, Any]:
    merged = [pr for pr in activity.pull_requests if pr.state == "MERGED" and pr.merged_at]
    merge_hours = [hours_between(pr.created_at, pr.merged_at) for pr in merged if pr.merged_at]
    review_hours = [
        hours
        for pr in activity.pull_requests
        if (hours := first_review_hours(pr, login)) is not None
    ]
    weeks = week_count(timeframe)
    return {
        "merge_hours_median": rounded(median(merge_hours)),
        "merge_hours_p75": rounded(percentile(merge_hours, 0.75)),
        "first_review_hours_median": rounded(median(review_hours)),
        "prs_with_review": len(review_hours),
        "prs_merged_per_week": round(len(merged) / weeks, 2) if weeks else 0.0,
        "weeks": round(weeks, 1),
    }


def collaboration_metrics(activity: Activity, login: str) -> dict[str, Any]:
    me = login.lower()
    authors_reviewed = {r.pr_author.lower() for r in activity.reviews if r.pr_author.lower() != me}
    reviewers = {
        review.author.lower()
        for pr in activity.pull_requests
        for review in pr.reviews
        if review.author.lower() != me
    }
    own_repos = {pr.repo for pr in activity.pull_requests} | {c.repo for c in activity.commits}
    review_repos = {review.repo for review in activity.reviews}
    return {
        "authors_reviewed": len(authors_reviewed),
        "reviewers_of_own_prs": len(reviewers),
        "reviews_per_pr_opened": ratio(len(activity.reviews), len(activity.pull_requests)),
        "repos_reviewed_in": len(review_repos),
        "repos_reviewed_only": len(review_repos - own_repos),
        "cross_repo_reach": len(own_repos | review_repos),
    }
