"""Themes, top pull requests, top repositories and repository share."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any

from impact_review.core.models import Activity, PullRequest
from impact_review.core.stats import ratio
from impact_review.core.themes import THEMES, classify

TOP_PRS = 15
TOP_REPOS = 10


def pr_score(pr: PullRequest, login: str) -> float:
    """Size on a log scale, plus review discussion, plus distinct reviewers counted twice."""
    reviewers = {r.author.lower() for r in pr.reviews if r.author.lower() != login.lower()}
    return round(math.log2(pr.lines + 1) + len(pr.reviews) + pr.comments + 2 * len(reviewers), 2)


def theme_metrics(activity: Activity) -> dict[str, Any]:
    grouped: dict[str, list[PullRequest]] = defaultdict(list)
    for pr in activity.pull_requests:
        grouped[classify(pr)].append(pr)
    return {
        theme: {
            "prs": len(grouped.get(theme, [])),
            "prs_merged": sum(1 for pr in grouped.get(theme, []) if pr.state == "MERGED"),
            "lines": sum(pr.lines for pr in grouped.get(theme, [])),
        }
        for theme in THEMES
    }


def top_pull_requests(activity: Activity, login: str) -> list[dict[str, Any]]:
    ranked = sorted(activity.pull_requests, key=lambda pr: pr_score(pr, login), reverse=True)
    return [
        {
            "repo": pr.repo,
            "number": pr.number,
            "title": pr.title,
            "url": pr.url,
            "state": pr.state,
            "theme": classify(pr),
            "lines": pr.lines,
            "files": pr.changed_files,
            "reviews": len(pr.reviews),
            "comments": pr.comments,
            "reviewers": len(
                {r.author.lower() for r in pr.reviews if r.author.lower() != login.lower()}
            ),
            "merged_at": pr.merged_at.date().isoformat() if pr.merged_at else None,
            "score": pr_score(pr, login),
        }
        for pr in ranked[:TOP_PRS]
    ]


def top_repositories(activity: Activity) -> list[dict[str, Any]]:
    commits = Counter(c.repo for c in activity.commits)
    prs = Counter(pr.repo for pr in activity.pull_requests)
    merged = Counter(pr.repo for pr in activity.pull_requests if pr.state == "MERGED")
    reviews = Counter(r.repo for r in activity.reviews)
    lines: Counter[str] = Counter()
    for pr in activity.pull_requests:
        if pr.state == "MERGED":
            lines[pr.repo] += pr.lines
    names = set(commits) | set(prs) | set(reviews)
    rows = [
        {
            "repo": name,
            "commits": commits[name],
            "prs": prs[name],
            "prs_merged": merged[name],
            "reviews": reviews[name],
            "lines": lines[name],
            "activity": commits[name] + prs[name] + reviews[name],
        }
        for name in names
    ]
    rows.sort(key=lambda row: (row["activity"], row["repo"]), reverse=True)
    return rows[:TOP_REPOS]


def repo_share_metrics(activity: Activity) -> dict[str, Any]:
    return {
        share.repo: {
            "commits": share.commits,
            "commits_total": share.commits_total,
            "commit_share": ratio(share.commits, share.commits_total),
            "lines": share.lines,
            "lines_total": share.lines_total,
            "line_share": ratio(share.lines, share.lines_total),
        }
        for share in sorted(activity.repo_shares, key=lambda s: s.commits, reverse=True)
    }
