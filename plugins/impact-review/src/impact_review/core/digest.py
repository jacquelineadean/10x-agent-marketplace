"""The compact Markdown digest Claude reads. Hard cap 12,000 bytes, about 3,000 tokens."""

from __future__ import annotations

from typing import Any

DIGEST_CAP_BYTES = 12_000
_TRUNCATED_NOTE = "\n_Digest trimmed to fit the 12 KB cap; metrics.json holds the full data._\n"


def _line(label: str, value: Any, key: str) -> str:
    return f"- {label}: {value} ({key})"


def _header(metrics: dict[str, Any]) -> list[str]:
    profile, frame = metrics["profile"], metrics["timeframe"]
    who = f"{profile['name']} (@{profile['login']})" if profile["name"] else f"@{profile['login']}"
    return [
        f"# Impact digest for {who}",
        "",
        f"Host: {metrics['host']}. Timeframe: {frame['since']} to {frame['until']} "
        f"({frame['label']}, {frame['days']} days). Generated {metrics['generated_at']}.",
        "Cite every number by its key in parentheses, for example (volume.prs_merged).",
        "",
    ]


def _volume(metrics: dict[str, Any]) -> list[str]:
    v, c = metrics["volume"], metrics["code"]
    bands = ", ".join(f"{name} {count}" for name, count in c["size_bands"].items())
    return [
        "## Volume and code",
        _line("Commits on default branches", v["commits"], "volume.commits"),
        _line("PRs opened", v["prs_opened"], "volume.prs_opened"),
        _line("PRs merged", v["prs_merged"], "volume.prs_merged"),
        _line("PRs closed unmerged", v["prs_closed_unmerged"], "volume.prs_closed_unmerged"),
        _line("PRs still open", v["prs_open"], "volume.prs_open"),
        _line(
            "Reviews given",
            f"{v['reviews']} (approved {v['reviews_approved']}, changes requested "
            f"{v['reviews_changes_requested']}, commented {v['reviews_commented']})",
            "volume.reviews",
        ),
        _line("Review comments written", v["review_comments"], "volume.review_comments"),
        _line("Issues opened", v["issues_opened"], "volume.issues_opened"),
        _line("Repos touched", v["repos_touched"], "volume.repos_touched"),
        _line("Orgs touched", v["orgs_touched"], "volume.orgs_touched"),
        _line("Languages (repos)", _top_items(v["languages"], 5), "volume.languages"),
        _line(
            "Restricted (private, hidden) contributions",
            v["restricted_contributions"],
            "volume.restricted_contributions",
        ),
        _line(
            "Lines added / deleted on merged PRs",
            f"{c['lines_added']} / {c['lines_deleted']}",
            "code.lines_added, code.lines_deleted",
        ),
        _line("Files changed on merged PRs", c["files_changed"], "code.files_changed"),
        _line("Median merged PR size (lines)", c["median_pr_lines"], "code.median_pr_lines"),
        _line("PR size bands", bands, "code.size_bands"),
        "",
    ]


def _flow_and_collaboration(metrics: dict[str, Any]) -> list[str]:
    f, col = metrics["flow"], metrics["collaboration"]
    return [
        "## Flow",
        _line("Median hours to merge", f["merge_hours_median"], "flow.merge_hours_median"),
        _line("75th percentile hours to merge", f["merge_hours_p75"], "flow.merge_hours_p75"),
        _line(
            "Median hours to first review",
            f["first_review_hours_median"],
            "flow.first_review_hours_median",
        ),
        _line("PRs merged per week", f["prs_merged_per_week"], "flow.prs_merged_per_week"),
        "",
        "## Collaboration",
        _line(
            "Distinct authors reviewed", col["authors_reviewed"], "collaboration.authors_reviewed"
        ),
        _line(
            "Distinct reviewers of own PRs",
            col["reviewers_of_own_prs"],
            "collaboration.reviewers_of_own_prs",
        ),
        _line(
            "Reviews given per PR opened",
            col["reviews_per_pr_opened"],
            "collaboration.reviews_per_pr_opened",
        ),
        _line("Repos reviewed in", col["repos_reviewed_in"], "collaboration.repos_reviewed_in"),
        _line(
            "Repos reached (own work plus reviews)",
            col["cross_repo_reach"],
            "collaboration.cross_repo_reach",
        ),
        "",
    ]


def _consistency(metrics: dict[str, Any]) -> list[str]:
    c = metrics["consistency"]
    months = ", ".join(f"{month} {count}" for month, count in c["by_month"].items())
    weekdays = ", ".join(f"{day} {count}" for day, count in c["by_weekday"].items())
    return [
        "## Consistency",
        _line(
            "Active days",
            f"{c['active_days']} of {c['days_in_timeframe']}",
            "consistency.active_days",
        ),
        _line("Longest streak (days)", c["longest_streak_days"], "consistency.longest_streak_days"),
        _line("Share of weeks active", c["active_weeks_share"], "consistency.active_weeks_share"),
        _line("Contributions by month", months, "consistency.by_month"),
        _line("Contributions by weekday", weekdays, "consistency.by_weekday"),
        "",
    ]


def _themes(metrics: dict[str, Any]) -> list[str]:
    rows = [
        f"- {theme}: {data['prs']} PRs, {data['prs_merged']} merged, {data['lines']} lines "
        f"(themes.{theme})"
        for theme, data in metrics["themes"].items()
        if data["prs"]
    ]
    return ["## Themes (PRs grouped by labels, title prefix and keywords)", *rows, ""]


def _repo_share(metrics: dict[str, Any]) -> list[str]:
    shares = metrics["repo_share"]
    if not shares:
        return []
    rows = [
        f"- {repo}: {d['commits']} of {d['commits_total']} commits ({d['commit_share']}), "
        f"{d['lines']} of {d['lines_total']} lines ({d['line_share']}) (repo_share.{repo})"
        for repo, d in list(shares.items())[:10]
    ]
    return ["## Share of repository work", *rows, ""]


def _top_repos(metrics: dict[str, Any]) -> list[str]:
    rows = [
        f"- {r['repo']}: {r['commits']} commits, {r['prs']} PRs ({r['prs_merged']} merged), "
        f"{r['reviews']} reviews, {r['lines']} merged lines (highlights.top_repos[{i}])"
        for i, r in enumerate(metrics["highlights"]["top_repos"])
    ]
    return ["## Top repositories", *rows, ""]


def _top_prs(metrics: dict[str, Any], limit: int) -> list[str]:
    rows = [
        f"- {pr['repo']}#{pr['number']} {pr['title']} ({pr['state'].lower()}, {pr['theme']}, "
        f"{pr['lines']} lines, {pr['files']} files, {pr['reviews']} reviews, "
        f"{pr['comments']} comments, "
        f"{pr['reviewers']} reviewers) (highlights.top_prs[{i}])"
        for i, pr in enumerate(metrics["highlights"]["top_prs"][:limit])
    ]
    return ["## Top pull requests (ranked by size, discussion and reach)", *rows, ""]


def _footer(metrics: dict[str, Any]) -> list[str]:
    lines = ["## Limits", *[f"- {limit}" for limit in metrics["limits"]]]
    if metrics["warnings"]:
        lines += ["", "## Warnings", *[f"- {warning}" for warning in metrics["warnings"][:10]]]
    return lines + [""]


def _top_items(counts: dict[str, int], limit: int) -> str:
    return ", ".join(f"{name} {count}" for name, count in list(counts.items())[:limit]) or "none"


def render_digest(metrics: dict[str, Any], cap_bytes: int = DIGEST_CAP_BYTES) -> str:
    """Render the digest; drop top PR rows, then truncate, until it fits `cap_bytes`."""
    top_limit = len(metrics["highlights"]["top_prs"])
    while True:
        text = "\n".join(
            _header(metrics)
            + _volume(metrics)
            + _flow_and_collaboration(metrics)
            + _consistency(metrics)
            + _themes(metrics)
            + _repo_share(metrics)
            + _top_repos(metrics)
            + _top_prs(metrics, top_limit)
            + _footer(metrics)
        )
        if len(text.encode("utf-8")) <= cap_bytes:
            return text
        if top_limit > 3:
            top_limit -= 1
            continue
        return _truncate(text, cap_bytes)


def _truncate(text: str, cap_bytes: int) -> str:
    budget = cap_bytes - len(_TRUNCATED_NOTE.encode("utf-8"))
    cut = text.encode("utf-8")[:budget].decode("utf-8", errors="ignore")
    return cut.rsplit("\n", 1)[0] + _TRUNCATED_NOTE
