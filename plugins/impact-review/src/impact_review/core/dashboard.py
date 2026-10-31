"""dashboard.md and dashboard.html rendered from metrics.json. Claude never reads these."""

from __future__ import annotations

from html import escape
from typing import Any

from impact_review.core.charts import bar_chart

_CSS = (
    "body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;"
    "color:#1a1a1a}table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;"
    "padding:4px 8px;text-align:left}th{background:#f3f3f3}svg{display:block;margin:1rem 0}"
    "h2{margin-top:2rem}"
)


def _table(headers: list[str], rows: list[list[Any]]) -> list[str]:
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return lines


def _summary_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    v, c, f, col = metrics["volume"], metrics["code"], metrics["flow"], metrics["collaboration"]
    cons = metrics["consistency"]
    people = (
        []
        if metrics["scope"]["individual"]
        else [["People active / in scope", f"{v['active_people']} / {v['people']}"]]
    )
    return [
        *people,
        ["Commits (default branches)", v["commits"]],
        [
            "PRs opened / merged / closed unmerged",
            f"{v['prs_opened']} / {v['prs_merged']} / {v['prs_closed_unmerged']}",
        ],
        ["Reviews given", v["reviews"]],
        ["Review comments", v["review_comments"]],
        ["Issues opened", v["issues_opened"]],
        ["Repos / orgs touched", f"{v['repos_touched']} / {v['orgs_touched']}"],
        ["Lines added / deleted (merged PRs)", f"{c['lines_added']} / {c['lines_deleted']}"],
        ["Median hours to merge / p75", f"{f['merge_hours_median']} / {f['merge_hours_p75']}"],
        ["Median hours to first review", f["first_review_hours_median"]],
        ["PRs merged per week", f["prs_merged_per_week"]],
        [
            "Authors reviewed / reviewers of own PRs",
            f"{col['authors_reviewed']} / {col['reviewers_of_own_prs']}",
        ],
        [
            "Active days / longest streak",
            f"{cons['active_days']} / {cons['longest_streak_days']}",
        ],
    ]


def _pr_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    return [
        [
            f"{pr['repo']}#{pr['number']}",
            pr["title"],
            pr["state"].lower(),
            pr["theme"],
            pr["lines"],
            pr["reviews"],
            pr["comments"],
            pr["reviewers"],
        ]
        for pr in metrics["highlights"]["top_prs"]
    ]


def _repo_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    return [
        [r["repo"], r["commits"], r["prs"], r["prs_merged"], r["reviews"], r["lines"]]
        for r in metrics["highlights"]["top_repos"]
    ]


def _theme_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    return [
        [t, d["prs"], d["prs_merged"], d["lines"]] for t, d in metrics["themes"].items() if d["prs"]
    ]


def _title(metrics: dict[str, Any]) -> str:
    frame = metrics["timeframe"]
    return f"Impact dashboard: {metrics['scope']['label']} {frame['since']} to {frame['until']}"


def _people_rows(metrics: dict[str, Any]) -> list[list[Any]]:
    if metrics["scope"]["individual"]:
        return []
    return [
        [
            f"@{login}",
            d["name"],
            d["prs_opened"],
            d["prs_merged"],
            d["reviews"],
            d["commits"],
            d["issues_opened"],
            d["lines_changed"],
            d["active_days"],
        ]
        for login, d in metrics["people"].items()
    ]


_PEOPLE_HEADERS = [
    "Person",
    "Name",
    "PRs",
    "Merged",
    "Reviews",
    "Commits",
    "Issues",
    "Lines",
    "Active days",
]


def _periods(metrics: dict[str, Any]) -> tuple[str, list[tuple[str, int]]]:
    """Months for up to 24 months of data, years beyond that."""
    c = metrics["consistency"]
    if len(c["by_month"]) > 24:
        return "year", list(c["by_year"].items())
    return "month", list(c["by_month"].items())


def render_dashboard_md(metrics: dict[str, Any]) -> str:
    lines = [
        f"# {_title(metrics)}",
        "",
        f"Host {metrics['host']}, generated {metrics['generated_at']}.",
        "",
    ]
    lines += ["## Summary", *_table(["Metric", "Value"], _summary_rows(metrics)), ""]
    if people := _people_rows(metrics):
        lines += ["## People", *_table(_PEOPLE_HEADERS, people), ""]
    lines += ["## Themes", *_table(["Theme", "PRs", "Merged", "Lines"], _theme_rows(metrics)), ""]
    lines += [
        "## Top repositories",
        *_table(["Repo", "Commits", "PRs", "Merged", "Reviews", "Lines"], _repo_rows(metrics)),
        "",
    ]
    lines += [
        "## Top pull requests",
        *_table(
            ["PR", "Title", "State", "Theme", "Lines", "Reviews", "Comments", "Reviewers"],
            _pr_rows(metrics),
        ),
        "",
    ]
    unit, periods = _periods(metrics)
    lines += [
        f"## Contributions by {unit}",
        *_table([unit.capitalize(), "Contributions"], [[p, n] for p, n in periods]),
        "",
    ]
    if metrics["repo_share"]:
        rows = [
            [
                repo,
                d["commits"],
                d["commits_total"],
                d["commit_share"],
                d["lines"],
                d["lines_total"],
                d["line_share"],
            ]
            for repo, d in metrics["repo_share"].items()
        ]
        lines += [
            "## Share of repository work",
            *_table(
                ["Repo", "Commits", "Repo commits", "Share", "Lines", "Repo lines", "Share"], rows
            ),
            "",
        ]
    lines += ["## Limits", *[f"- {limit}" for limit in metrics["limits"]]]
    if metrics["warnings"]:
        lines += ["", "## Warnings", *[f"- {w}" for w in metrics["warnings"]]]
    return "\n".join(lines) + "\n"


def _html_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>" for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def render_dashboard_html(metrics: dict[str, Any]) -> str:
    """One self-contained HTML file: inline CSS and inline SVG, no scripts or remote assets."""
    c = metrics["consistency"]
    unit, periods = _periods(metrics)
    charts = [
        bar_chart(f"Contributions by {unit}", periods),
        bar_chart("Contributions by weekday", list(c["by_weekday"].items()), "#5b9a3c"),
        bar_chart(
            "Merged PR size bands (lines)", list(metrics["code"]["size_bands"].items()), "#c97b1a"
        ),
        bar_chart(
            "PRs by theme",
            [(t, d["prs"]) for t, d in metrics["themes"].items() if d["prs"]],
            "#8a4fbf",
        ),
    ]
    sections = [
        f"<h1>{escape(_title(metrics))}</h1>",
        f"<p>Host {escape(metrics['host'])}, generated {escape(metrics['generated_at'])}.</p>",
        "<h2>Summary</h2>",
        _html_table(["Metric", "Value"], _summary_rows(metrics)),
        *(
            ["<h2>People</h2>", _html_table(_PEOPLE_HEADERS, people)]
            if (people := _people_rows(metrics))
            else []
        ),
        "<h2>Charts</h2>",
        *charts,
        "<h2>Top repositories</h2>",
        _html_table(["Repo", "Commits", "PRs", "Merged", "Reviews", "Lines"], _repo_rows(metrics)),
        "<h2>Top pull requests</h2>",
        _html_table(
            ["PR", "Title", "State", "Theme", "Lines", "Reviews", "Comments", "Reviewers"],
            _pr_rows(metrics),
        ),
        "<h2>Limits</h2><ul>"
        + "".join(f"<li>{escape(limit)}</li>" for limit in metrics["limits"])
        + "</ul>",
    ]
    if metrics["warnings"]:
        sections.append(
            "<h2>Warnings</h2><ul>"
            + "".join(f"<li>{escape(w)}</li>" for w in metrics["warnings"])
            + "</ul>"
        )
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{escape(_title(metrics))}</title><style>{_CSS}</style></head><body>"
        + "".join(sections)
        + "</body></html>\n"
    )
