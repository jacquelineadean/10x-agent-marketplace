"""GitHubSource: every GitHub call the collector makes, with caching and year chunking."""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from impact_review.connectors.github import queries
from impact_review.connectors.github.cache import RawCache
from impact_review.connectors.github.http import GitHubTransport
from impact_review.connectors.github.parse import (
    parse_calendar,
    parse_commit,
    parse_issue,
    parse_profile,
    parse_pull_request,
    parse_repo_share,
    parse_repositories,
    parse_review,
    parse_totals,
)
from impact_review.core.models import Activity, Profile, Repository, Timeframe, Totals
from impact_review.core.timeframe import end_of, start_of, year_chunks

log = logging.getLogger(__name__)
T = TypeVar("T")

STATS_ATTEMPTS = 3
STATS_WAIT_SECONDS = 2.0


def _iso(moment: datetime) -> str:
    return moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


class GitHubSource:
    def __init__(self, transport: GitHubTransport) -> None:
        self.transport = transport
        self.cache: RawCache | None = None
        self.warnings: list[str] = []

    def enable_cache(self, folder: Path, refresh: bool) -> None:
        self.cache = RawCache(folder, refresh)

    def profile(self) -> Profile:
        data, _ = self.transport.graphql(queries.VIEWER, {})
        return parse_profile(data)

    def collect(
        self, timeframe: Timeframe, profile: Profile, orgs: Sequence[str], repo_share: bool
    ) -> Activity:
        wanted = {org.lower() for org in orgs}
        activity = Activity()
        chunks = year_chunks(timeframe)
        for start, stop in chunks:
            variables = {"from": _iso(start), "to": _iso(stop)}
            self._collect_summary(activity, variables)
            self._collect_lists(activity, variables)
        self._keep_orgs(activity, wanted)
        self._dedupe(activity)
        self._collect_commits(activity, timeframe, profile)
        if repo_share:
            self._collect_repo_shares(activity, timeframe, profile)
        activity.warnings.extend(self.warnings)
        return activity

    def _query(self, name: str, document: str, variables: dict[str, Any]) -> Any:
        if self.cache and (cached := self.cache.get(name, variables)) is not None:
            return cached
        data, errors = self.transport.graphql(document, variables)
        for message in errors:
            self._warn(f"GitHub returned partial data for {name}: {message}")
        if self.cache:
            self.cache.put(name, variables, data)
        return data

    def _pages(
        self, name: str, document: str, variables: dict[str, Any], *path: str
    ) -> Iterator[Any]:
        cursor: str | None = None
        while True:
            data = self._query(name, document, {**variables, "after": cursor})
            connection: Any = data
            for key in path:
                connection = (connection or {}).get(key)
            connection = connection or {}
            yield from (node for node in connection.get("nodes") or [] if node)
            page = connection.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                return
            cursor = page.get("endCursor")

    def _collect_summary(self, activity: Activity, variables: dict[str, Any]) -> None:
        data = self._query("contributions", queries.CONTRIBUTIONS, variables)
        collection = data["viewer"]["contributionsCollection"]
        totals = parse_totals(collection)
        activity.totals = Totals(
            commits=activity.totals.commits + totals.commits,
            pull_requests=activity.totals.pull_requests + totals.pull_requests,
            reviews=activity.totals.reviews + totals.reviews,
            issues=activity.totals.issues + totals.issues,
            restricted=activity.totals.restricted + totals.restricted,
        )
        for day, count in parse_calendar(collection).items():
            activity.calendar[day] = activity.calendar.get(day, 0) + count
        activity.repositories.extend(parse_repositories(collection))

    def _collect_lists(self, activity: Activity, variables: dict[str, Any]) -> None:
        collection = ("viewer", "contributionsCollection")
        for node in self._pages(
            "pull_requests",
            queries.PULL_REQUESTS,
            variables,
            *collection,
            "pullRequestContributions",
        ):
            if node.get("pullRequest"):
                activity.pull_requests.append(parse_pull_request(node["pullRequest"]))
        for node in self._pages(
            "reviews", queries.REVIEWS, variables, *collection, "pullRequestReviewContributions"
        ):
            if node.get("pullRequestReview"):
                activity.reviews.append(parse_review(node["pullRequestReview"]))
        for node in self._pages(
            "issues", queries.ISSUES, variables, *collection, "issueContributions"
        ):
            if node.get("issue"):
                activity.issues.append(parse_issue(node["issue"]))

    def _collect_commits(self, activity: Activity, timeframe: Timeframe, profile: Profile) -> None:
        since, until = _iso(start_of(timeframe.since)), _iso(end_of(timeframe.until))
        for repo in activity.repositories:
            if repo.default_branch is None:
                self._warn(f"{repo.name} has no default branch; commits skipped")
                continue
            owner, name = repo.name.split("/", 1)
            variables = {
                "owner": owner,
                "name": name,
                "since": since,
                "until": until,
                "author": profile.node_id,
            }
            for node in self._pages(
                "commits",
                queries.COMMITS,
                variables,
                "repository",
                "defaultBranchRef",
                "target",
                "history",
            ):
                activity.commits.append(parse_commit(node, repo.name, repo.owner))

    def _collect_repo_shares(
        self, activity: Activity, timeframe: Timeframe, profile: Profile
    ) -> None:
        for repo in activity.repositories:
            rows = self._contributor_stats(repo)
            if rows is None:
                self._warn(
                    f"{repo.name}: contributor statistics not ready after "
                    f"{STATS_ATTEMPTS} attempts; repo share skipped"
                )
                continue
            activity.repo_shares.append(
                parse_repo_share(repo.name, profile.login, timeframe.since, timeframe.until, rows)
            )

    def _contributor_stats(self, repo: Repository) -> list[Any] | None:
        """REST answers 202 while it computes statistics; wait and retry up to three times."""
        variables = {"repo": repo.name}
        if self.cache and (cached := self.cache.get("stats_contributors", variables)) is not None:
            return list(cached)
        for attempt in range(1, STATS_ATTEMPTS + 1):
            response = self.transport.rest_get(f"repos/{repo.name}/stats/contributors")
            if response.status == 200 and isinstance(response.body, list):
                if self.cache:
                    self.cache.put("stats_contributors", variables, response.body)
                return response.body
            if attempt < STATS_ATTEMPTS:
                self.transport.sleeper(STATS_WAIT_SECONDS * attempt)
        return None

    def _keep_orgs(self, activity: Activity, wanted: set[str]) -> None:
        if not wanted:
            return
        activity.repositories = [r for r in activity.repositories if r.owner.lower() in wanted]
        activity.pull_requests = [p for p in activity.pull_requests if p.owner.lower() in wanted]
        activity.reviews = [r for r in activity.reviews if r.owner.lower() in wanted]
        activity.issues = [i for i in activity.issues if i.owner.lower() in wanted]

    def _dedupe(self, activity: Activity) -> None:
        """Year chunks can repeat a repository or an item at a boundary; keep the first copy."""
        activity.repositories = _unique(activity.repositories, lambda r: r.name)
        activity.pull_requests = _unique(activity.pull_requests, lambda p: p.url)
        activity.reviews = _unique(activity.reviews, lambda r: (r.pr_url, r.submitted_at))
        activity.issues = _unique(activity.issues, lambda i: i.url)

    def _warn(self, message: str) -> None:
        log.warning("%s", message)
        self.warnings.append(message)


def _unique(items: list[T], key: Callable[[T], Any]) -> list[T]:
    seen: set[Any] = set()
    kept = []
    for item in items:
        marker = key(item)
        if marker in seen:
            continue
        seen.add(marker)
        kept.append(item)
    return kept
