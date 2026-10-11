"""Assemble metrics.json from the collected activity. Pure: no files, no network."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from impact_review.core.cadence import consistency_metrics
from impact_review.core.highlights import (
    repo_share_metrics,
    theme_metrics,
    top_pull_requests,
    top_repositories,
)
from impact_review.core.metrics import (
    code_metrics,
    collaboration_metrics,
    flow_metrics,
    volume_metrics,
)
from impact_review.core.models import Activity, Profile, Timeframe

SCHEMA_VERSION = 1

LIMITS = (
    "GitHub counts commits on default branches only; work merged by squash still "
    "counts through pull request metrics.",
    "Lines of code are shown next to pull request and review counts, never alone.",
)


def build_metrics(
    profile: Profile,
    timeframe: Timeframe,
    activity: Activity,
    host: str,
    generated_at: datetime,
) -> dict[str, Any]:
    """Return the full metrics document; keys are the citation paths the writer uses."""
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "host": host,
        "profile": {"login": profile.login, "name": profile.name},
        "timeframe": {
            "since": timeframe.since.isoformat(),
            "until": timeframe.until.isoformat(),
            "label": timeframe.label,
            "days": timeframe.days,
        },
        "volume": volume_metrics(activity),
        "code": code_metrics(activity),
        "flow": flow_metrics(activity, timeframe, profile.login),
        "collaboration": collaboration_metrics(activity, profile.login),
        "consistency": consistency_metrics(activity.calendar, timeframe),
        "themes": theme_metrics(activity),
        "repo_share": repo_share_metrics(activity),
        "highlights": {
            "top_prs": top_pull_requests(activity, profile.login),
            "top_repos": top_repositories(activity),
        },
        "limits": list(LIMITS),
        "warnings": list(activity.warnings),
    }
