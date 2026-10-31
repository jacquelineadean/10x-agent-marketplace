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
    people_metrics,
    volume_metrics,
)
from impact_review.core.models import Activity, Timeframe
from impact_review.core.scope import Scope

SCHEMA_VERSION = 2

LIMITS = (
    "GitHub counts commits on default branches only; work merged by squash still "
    "counts through pull request metrics.",
    "Lines of code are shown next to pull request and review counts, never alone.",
    "GitHub shows another person's contributions only in repositories the token can read.",
)


def scope_metrics(scope: Scope, orgs: list[str]) -> dict[str, Any]:
    return {
        "kind": scope.kind,
        "targets": list(scope.targets),
        "label": scope.label,
        "individual": scope.is_individual,
        "people": len(scope.people),
        "orgs": orgs,
    }


def build_metrics(
    scope: Scope,
    timeframe: Timeframe,
    activity: Activity,
    host: str,
    generated_at: datetime,
    orgs: list[str] | None = None,
) -> dict[str, Any]:
    """Return the full metrics document; keys are the citation paths the writer uses.

    `orgs` are the repository owners the run kept (empty means every owner).
    """
    people = people_metrics(activity, scope.people)
    volume = volume_metrics(activity)
    volume["people"] = len(scope.people)
    volume["active_people"] = sum(
        1 for row in people.values() if row["active_days"] or row["prs_opened"] or row["reviews"]
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(timespec="seconds"),
        "host": host,
        "scope": scope_metrics(scope, sorted(orgs if orgs is not None else scope.orgs)),
        "timeframe": {
            "since": timeframe.since.isoformat(),
            "until": timeframe.until.isoformat(),
            "label": timeframe.label,
            "days": timeframe.days,
        },
        "volume": volume,
        "code": code_metrics(activity),
        "flow": flow_metrics(activity, timeframe, len(scope.people)),
        "collaboration": collaboration_metrics(activity, scope.logins),
        "consistency": consistency_metrics(activity.calendar, timeframe),
        "themes": theme_metrics(activity),
        "repo_share": repo_share_metrics(activity),
        "highlights": {
            "top_prs": top_pull_requests(activity),
            "top_repos": top_repositories(activity),
        },
        "people": people,
        "limits": list(LIMITS),
        "warnings": list(activity.warnings),
    }
