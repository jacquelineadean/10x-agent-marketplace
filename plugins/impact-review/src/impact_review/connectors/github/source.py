"""GitHubSource: every GitHub call the collector makes, with caching and year chunking.

Scope lookups resolve people (the token owner, named users, team, organization or enterprise
members). Collection then runs each person's contributionsCollection through
`user(login:)`, chunked by year, and merges the results.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypeVar

from impact_review.connectors.github import queries
from impact_review.connectors.github.cache import RawCache
from impact_review.connectors.github.errors import GitHubError
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
from impact_review.core.scope import Scope, ScopeRequest
from impact_review.core.timeframe import end_of, start_of, year_chunks

log = logging.getLogger(__name__)
T = TypeVar("T")

STATS_ATTEMPTS = 3
STATS_WAIT_SECONDS = 2.0
_COLLECTION = ("user", "contributionsCollection")


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
        """The token's owner. Never cached: it is the first call and checks the token."""
        data, _ = self.transport.graphql(queries.VIEWER, {})
        return parse_profile(data["viewer"])

    # Scope resolution -------------------------------------------------------------------

    def resolve(self, request: ScopeRequest) -> tuple[list[Profile], list[str]]:
        if request.kind == "me":
            return [self.profile()], []
        if request.kind == "user":
            return [self._user(login) for login in request.targets], []
        if request.kind == "team":
            people: list[Profile] = []
            for target in request.targets:
                org, slug = target.split("/", 1)
                people.extend(self._team_members(org, slug))
            return people, [t.split("/", 1)[0] for t in request.targets]
        if request.kind == "org":
            people = [p for org in request.targets for p in self._org_members(org)]
            return people, list(request.targets)
        orgs = self._enterprise_orgs(request.targets[0])
        return [p for org in orgs for p in self._org_members(org)], orgs

    def _user(self, login: str) -> Profile:
        data, _ = self.transport.graphql(queries.USER, {"login": login})
        if not data.get("user"):
            raise GitHubError(f"GitHub user {login!r} not found on this host")
        return parse_profile(data["user"])

    def _team_members(self, org: str, slug: str) -> list[Profile]:
        nodes = self._pages(
            "team_members",
            queries.TEAM_MEMBERS,
            {"org": org, "slug": slug},
            "organization",
            "team",
            "members",
            missing=f"team {org}/{slug} not found, or the token lacks read:org for {org}",
        )
        return [parse_profile(node) for node in nodes]

    def _org_members(self, org: str) -> list[Profile]:
        nodes = self._pages(
            "org_members",
            queries.ORG_MEMBERS,
            {"org": org},
            "organization",
            "membersWithRole",
            missing=f"organization {org} not found, or the token lacks read:org",
        )
        return [parse_profile(node) for node in nodes]

    def _enterprise_orgs(self, slug: str) -> list[str]:
        nodes = self._pages(
            "enterprise_orgs",
            queries.ENTERPRISE_ORGS,
            {"slug": slug},
            "enterprise",
            "organizations",
            missing=f"enterprise {slug} not found, or the token lacks read:enterprise",
        )
        return [str(node["login"]) for node in nodes]

    # Collection -------------------------------------------------------------------------

    def collect(
        self, timeframe: Timeframe, scope: Scope, orgs: Sequence[str], repo_share: bool
    ) -> Activity:
        wanted = {org.lower() for org in orgs}
        activity = Activity()
        for person in scope.people:
            self._collect_person(activity, timeframe, person, wanted)
        activity.repositories = _unique(activity.repositories, lambda r: r.name)
        self._dedupe(activity)
        if repo_share:
            self._collect_repo_shares(activity, timeframe, scope.logins)
        activity.warnings.extend(self.warnings)
        return activity

    def _collect_person(
        self, activity: Activity, timeframe: Timeframe, person: Profile, wanted: set[str]
    ) -> None:
        mine = Activity()
        for start, stop in year_chunks(timeframe):
            variables = {"login": person.login, "from": _iso(start), "to": _iso(stop)}
            self._collect_summary(mine, variables)
            self._collect_lists(mine, variables, person.login)
        mine.repositories = _unique(mine.repositories, lambda r: r.name)
        self._keep_orgs(mine, wanted)
        self._collect_commits(mine, timeframe, person)
        self._merge(activity, mine, person.login.lower())

    def _merge(self, into: Activity, part: Activity, login: str) -> None:
        into.totals = Totals(
            commits=into.totals.commits + part.totals.commits,
            pull_requests=into.totals.pull_requests + part.totals.pull_requests,
            reviews=into.totals.reviews + part.totals.reviews,
            issues=into.totals.issues + part.totals.issues,
            restricted=into.totals.restricted + part.totals.restricted,
        )
        for day, count in part.calendar.items():
            into.calendar[day] = into.calendar.get(day, 0) + count
        into.calendars[login] = dict(part.calendar)
        into.repositories.extend(part.repositories)
        into.pull_requests.extend(part.pull_requests)
        into.reviews.extend(part.reviews)
        into.issues.extend(part.issues)
        into.commits.extend(part.commits)

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
        self,
        name: str,
        document: str,
        variables: dict[str, Any],
        *path: str,
        missing: str | None = None,
    ) -> Iterator[Any]:
        """Follow `path` to a connection and yield its nodes page by page.

        With `missing` set, a null anywhere on the path raises GitHubError with that message.
        """
        cursor: str | None = None
        while True:
            data = self._query(name, document, {**variables, "after": cursor})
            connection: Any = data
            for key in path:
                connection = (connection or {}).get(key)
                if connection is None and missing:
                    raise GitHubError(missing)
            connection = connection or {}
            yield from (node for node in connection.get("nodes") or [] if node)
            page = connection.get("pageInfo") or {}
            if not page.get("hasNextPage"):
                return
            cursor = page.get("endCursor")

    def _collect_summary(self, activity: Activity, variables: dict[str, Any]) -> None:
        data = self._query("contributions", queries.CONTRIBUTIONS, variables)
        user = data.get("user")
        if not user:
            raise GitHubError(f"GitHub user {variables['login']!r} not found on this host")
        collection = user["contributionsCollection"]
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

    def _collect_lists(self, activity: Activity, variables: dict[str, Any], login: str) -> None:
        for node in self._pages(
            "pull_requests",
            queries.PULL_REQUESTS,
            variables,
            *_COLLECTION,
            "pullRequestContributions",
        ):
            if node.get("pullRequest"):
                activity.pull_requests.append(parse_pull_request(node["pullRequest"], login))
        for node in self._pages(
            "reviews", queries.REVIEWS, variables, *_COLLECTION, "pullRequestReviewContributions"
        ):
            if node.get("pullRequestReview"):
                activity.reviews.append(parse_review(node["pullRequestReview"], login))
        for node in self._pages(
            "issues", queries.ISSUES, variables, *_COLLECTION, "issueContributions"
        ):
            if node.get("issue"):
                activity.issues.append(parse_issue(node["issue"], login))

    def _collect_commits(self, activity: Activity, timeframe: Timeframe, person: Profile) -> None:
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
                "author": person.node_id,
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
                activity.commits.append(parse_commit(node, repo.name, repo.owner, person.login))

    def _collect_repo_shares(
        self, activity: Activity, timeframe: Timeframe, logins: frozenset[str]
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
                parse_repo_share(repo.name, logins, timeframe.since, timeframe.until, rows)
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
        """Year chunks repeat items at a boundary; two people can share a commit. Keep one."""
        activity.pull_requests = _unique(activity.pull_requests, lambda p: p.url)
        activity.reviews = _unique(
            activity.reviews, lambda r: (r.pr_url, r.submitted_at, r.reviewer.lower())
        )
        activity.issues = _unique(activity.issues, lambda i: i.url)
        activity.commits = _unique(activity.commits, lambda c: (c.repo, c.oid))

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
