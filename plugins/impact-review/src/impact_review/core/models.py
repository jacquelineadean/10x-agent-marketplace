"""Domain records the collector fills and the metric rules read."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass(frozen=True)
class Profile:
    login: str
    name: str
    node_id: str
    created_at: date | None = None


@dataclass(frozen=True)
class Timeframe:
    """Inclusive date range of one run."""

    since: date
    until: date
    label: str

    @property
    def days(self) -> int:
        return (self.until - self.since).days + 1


@dataclass(frozen=True)
class Repository:
    name: str
    owner: str
    is_private: bool
    language: str | None
    default_branch: str | None


@dataclass(frozen=True)
class Review:
    """A review someone left on a pull request opened by a person in scope."""

    author: str
    state: str
    submitted_at: datetime | None


@dataclass(frozen=True)
class PullRequest:
    repo: str
    owner: str
    number: int
    title: str
    url: str
    state: str
    is_draft: bool
    created_at: datetime
    merged_at: datetime | None
    closed_at: datetime | None
    additions: int
    deletions: int
    changed_files: int
    labels: tuple[str, ...]
    reviews: tuple[Review, ...]
    comments: int
    language: str | None
    is_private: bool
    author: str = ""

    @property
    def lines(self) -> int:
        return self.additions + self.deletions


@dataclass(frozen=True)
class ReviewGiven:
    repo: str
    owner: str
    pr_number: int
    pr_title: str
    pr_url: str
    pr_author: str
    state: str
    submitted_at: datetime
    comments: int
    reviewer: str = ""


@dataclass(frozen=True)
class Issue:
    repo: str
    owner: str
    number: int
    title: str
    url: str
    state: str
    created_at: datetime
    closed_at: datetime | None
    labels: tuple[str, ...]
    author: str = ""


@dataclass(frozen=True)
class Commit:
    repo: str
    owner: str
    oid: str
    committed_at: datetime
    headline: str
    additions: int
    deletions: int
    changed_files: int
    pr_number: int | None
    author: str = ""


@dataclass(frozen=True)
class RepoShare:
    """The scope's part of a repository's commits and lines (REST contributor statistics)."""

    repo: str
    commits: int
    commits_total: int
    lines: int
    lines_total: int


@dataclass(frozen=True)
class Totals:
    """Counts GitHub reports in contributionsCollection, summed over year chunks."""

    commits: int = 0
    pull_requests: int = 0
    reviews: int = 0
    issues: int = 0
    restricted: int = 0


@dataclass
class Activity:
    """Everything one run collected for the people in scope inside the timeframe.

    Each pull request, issue and commit carries its `author`, each review its `reviewer`.
    `calendar` sums every person's daily counts; `calendars` keeps them per lowercase login.
    """

    totals: Totals = field(default_factory=Totals)
    calendar: dict[date, int] = field(default_factory=dict)
    calendars: dict[str, dict[date, int]] = field(default_factory=dict)
    repositories: list[Repository] = field(default_factory=list)
    pull_requests: list[PullRequest] = field(default_factory=list)
    reviews: list[ReviewGiven] = field(default_factory=list)
    issues: list[Issue] = field(default_factory=list)
    commits: list[Commit] = field(default_factory=list)
    repo_shares: list[RepoShare] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
