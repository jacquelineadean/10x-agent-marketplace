"""Shared test doubles: a fake HTTP opener that serves recorded GitHub responses."""

from __future__ import annotations

import io
import json
import re
import urllib.error
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from email.message import Message
from pathlib import Path
from typing import Any

import pytest
from impact_review.connectors.github.hosts import endpoints_for
from impact_review.connectors.github.http import GitHubTransport
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.models import Timeframe

FIXTURES = Path(__file__).parent / "fixtures"
TODAY = date(2026, 10, 11)
TIMEFRAME = Timeframe(since=date(2026, 1, 1), until=date(2026, 9, 30), label="ytd")
TOKEN = "ghp_test_token_never_printed"  # noqa: S105  fake credential for tests only


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@dataclass
class Reply:
    status: int = 200
    body: Any = None
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Sent:
    method: str
    url: str
    headers: dict[str, str]
    operation: str | None
    variables: dict[str, Any]
    query: str | None


class _Raw:
    def __init__(self, reply: Reply) -> None:
        self.status = reply.status
        self.headers = Message()
        for key, value in reply.headers.items():
            self.headers[key] = value
        self._data = b"" if reply.body is None else json.dumps(reply.body).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Raw:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeGitHub:
    """Serves replies keyed by GraphQL operation name (plus cursor) or REST path."""

    def __init__(self) -> None:
        self.replies: dict[str, list[Reply]] = {}
        self.sent: list[Sent] = []
        self.sleeps: list[float] = []

    def on(self, key: str, *replies: Reply) -> FakeGitHub:
        self.replies.setdefault(key, []).extend(replies)
        return self

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def __call__(self, request: Any, timeout: float) -> _Raw:
        sent = _describe(request)
        self.sent.append(sent)
        key = _key(sent)
        queue = self.replies.get(key) or self.replies.get(sent.operation or "")
        if not queue:
            raise AssertionError(f"no recorded reply for {key}")
        reply = queue.pop(0) if len(queue) > 1 else queue[0]
        if reply.status >= 400:
            headers = Message()
            for name, value in reply.headers.items():
                headers[name] = value
            body = b"" if reply.body is None else json.dumps(reply.body).encode()
            raise urllib.error.HTTPError(sent.url, reply.status, "error", headers, io.BytesIO(body))
        return _Raw(reply)

    def calls(self, operation: str) -> list[Sent]:
        return [s for s in self.sent if s.operation == operation]


def _describe(request: Any) -> Sent:
    headers = dict(request.header_items())
    operation, variables, query = None, {}, None
    if request.data:
        payload = json.loads(request.data.decode())
        query = payload["query"]
        match = re.search(r"\b(query|mutation)\s+(\w+)", query)
        operation = match.group(2) if match else None
        variables = payload.get("variables") or {}
    else:
        operation = request.full_url.split("/api.github.com/", 1)[-1].split("/v3/", 1)[-1]
    return Sent(request.get_method(), request.full_url, headers, operation, variables, query)


def _key(sent: Sent) -> str:
    if sent.query is None:
        return sent.operation or sent.url
    suffix = ""
    if sent.variables.get("after"):
        suffix = f"@{sent.variables['after']}"
    if sent.operation == "Commits" and "owner" in sent.variables:
        suffix = f":{sent.variables['owner']}/{sent.variables['name']}" + suffix
    return f"{sent.operation}{suffix}"


def recorded_github() -> FakeGitHub:
    """The standard recording: one viewer, four PRs over two pages, three reviews, one issue."""
    fake = FakeGitHub()
    fake.on("Viewer", Reply(body=fixture("viewer")))
    fake.on("Contributions", Reply(body=fixture("contributions")))
    fake.on("PullRequests", Reply(body=fixture("pull_requests_page1")))
    fake.on("PullRequests@cursor-1", Reply(body=fixture("pull_requests_page2")))
    fake.on("Reviews", Reply(body=fixture("reviews_page1")))
    fake.on("Issues", Reply(body=fixture("issues_page1")))
    fake.on("Commits:acme/api", Reply(body=fixture("commits_acme_api")))
    fake.on("Commits:acme/web", Reply(body=fixture("commits_acme_web")))
    fake.on("Commits:partners/sdk", Reply(body=fixture("commits_partners_sdk")))
    fake.on(
        "repos/acme/api/stats/contributors",
        Reply(status=202),
        Reply(body=fixture("stats_contributors_acme_api")),
    )
    fake.on("repos/acme/web/stats/contributors", Reply(body=fixture("stats_contributors_acme_web")))
    fake.on(
        "repos/partners/sdk/stats/contributors",
        Reply(status=202),
        Reply(status=202),
        Reply(status=202),
    )
    return fake


def transport_for(fake: FakeGitHub, host: str = "github.com") -> GitHubTransport:
    return GitHubTransport(endpoints_for(host), TOKEN, opener=fake, sleeper=fake.sleep)


@pytest.fixture
def github() -> FakeGitHub:
    return recorded_github()


@pytest.fixture
def source(github: FakeGitHub) -> GitHubSource:
    return GitHubSource(transport_for(github))


SourceBuilder = Callable[[FakeGitHub], GitHubSource]
