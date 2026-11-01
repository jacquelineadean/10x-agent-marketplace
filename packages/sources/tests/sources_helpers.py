"""Small facts and queries files, recorded replies and fake programs for the sources tests."""

from __future__ import annotations

import io
import json
import subprocess
import urllib.error
import urllib.parse
from dataclasses import dataclass, field
from email.message import Message
from pathlib import Path
from typing import Any

from sources.connectors.wire import Wire

TODAY = "2026-10-31"


def facts() -> dict[str, Any]:
    return {
        "github": {
            "merged": {"value": 1240, "source": "github", "note": "merged PRs, Q3 2026"},
            "weekly": {"x": ["2026-07-06", "2026-07-13", "2026-07-20"], "merged": [81, 63, 102]},
        },
        "jira": {"epics_done": {"value": 9, "unit": "epics", "source": "jira"}},
        "derive": {"github.merged_last": {"fn": "last", "of": "github.weekly.merged"}},
    }


def queries() -> dict[str, Any]:
    entry = {
        "lane": "mcp",
        "window": {"start": "2026-07-01", "end": "2026-09-30"},
        "as_of": TODAY,
    }
    return {
        "schema_version": 1,
        "queries": {
            "github": {
                **entry,
                "system": "github",
                "connection": "github",
                "query": 'search_issues q="is:pr is:merged merged:2026-07-01..2026-09-30"',
            },
            "jira.epics_done": {
                **entry,
                "system": "jira",
                "connection": "claude_ai_Atlassian",
                "query": "JQL project = SHOP AND issuetype = Epic AND statusCategory = Done",
            },
        },
    }


# Recorded replies for the collectors -------------------------------------------------

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> Any:
    """A recorded response body, such as `datadog/query_daily`."""
    path = FIXTURES / name
    return json.loads(path.read_text(encoding="utf-8")) if path.suffix == ".json" else path


def text_fixture(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


@dataclass
class Reply:
    body: Any = None
    status: int = 200
    headers: dict[str, str] = field(default_factory=dict)


@dataclass
class Sent:
    method: str
    path: str
    params: dict[str, list[str]]
    headers: dict[str, str]
    body: Any


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


class FakeWeb:
    """Serves recorded replies by method, path and query parameters; keeps every request."""

    def __init__(self) -> None:
        self.routes: list[tuple[str, str, dict[str, str], list[Reply]]] = []
        self.sent: list[Sent] = []
        self.sleeps: list[float] = []

    def on(
        self, method: str, path: str, *replies: Reply, where: dict[str, str] | None = None
    ) -> FakeWeb:
        self.routes.append((method, path, where or {}, list(replies)))
        return self

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def __call__(self, request: Any, timeout: float) -> _Raw:
        url = urllib.parse.urlsplit(request.full_url)
        params = urllib.parse.parse_qs(url.query)
        body = json.loads(request.data.decode()) if request.data else None
        sent = Sent(request.get_method(), url.path, params, dict(request.header_items()), body)
        self.sent.append(sent)
        for method, path, where, replies in self.routes:
            if (
                method == sent.method
                and path == sent.path
                and all(params.get(k, [""])[0] == v for k, v in where.items())
            ):
                reply = replies.pop(0) if len(replies) > 1 else replies[0]
                if reply.status >= 400:
                    headers = Message()
                    for name, value in reply.headers.items():
                        headers[name] = value
                    data = io.BytesIO(json.dumps(reply.body or {}).encode())
                    raise urllib.error.HTTPError(request.full_url, reply.status, "", headers, data)
                return _Raw(reply)
        raise AssertionError(f"no recorded reply for {sent.method} {sent.path} {params}")


@dataclass
class FakeProgram:
    """Stands in for psql or SQLcl: keeps the call and prints a recorded result."""

    stdout: str = ""
    stderr: str = ""
    returncode: int = 0
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, argv: list[str], **options: Any) -> subprocess.CompletedProcess[str]:
        self.calls.append({"argv": argv, **options})
        return subprocess.CompletedProcess(argv, self.returncode, self.stdout, self.stderr)


def wire(web: FakeWeb | None = None, program: FakeProgram | None = None, **environ: str) -> Wire:
    """A Wire on recorded replies, with psql and sql installed and no gh sign-in."""
    web = web or FakeWeb()
    return Wire(
        opener=web,
        sleeper=web.sleep,
        runner=program or FakeProgram(),
        which=lambda name: f"/usr/bin/{name}",
        gh_token=lambda host: None,
        environ=environ,
    )
