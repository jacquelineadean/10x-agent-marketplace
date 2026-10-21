"""Shared test doubles for perf-ratchet: a fake HTTP opener, sample projects and series."""

from __future__ import annotations

import io
import json
import urllib.error
from dataclasses import dataclass, field
from datetime import date, timedelta
from email.message import Message
from pathlib import Path
from typing import Any

from perf_ratchet.core.model import Point, Project
from perf_ratchet.core.project import parse_project

FIXTURES = Path(__file__).parent / "fixtures"
DEMO = Path(__file__).parents[1] / "examples" / "demo"
API_KEY = "dd-api-key-never-printed"  # noqa: S105  fake credential for tests only
APP_KEY = "dd-app-key-never-printed"  # noqa: S105  fake credential for tests only


def fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


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
    body: Any


class _Raw:
    def __init__(self, reply: Reply) -> None:
        self._data = b"" if reply.body is None else json.dumps(reply.body).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Raw:
        return self

    def __exit__(self, *_: object) -> None:
        return None


class FakeHttp:
    """Serves queued replies in order; records every request."""

    def __init__(self, *replies: Reply) -> None:
        self.replies = list(replies)
        self.sent: list[Sent] = []
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)

    def __call__(self, request: Any, timeout: float) -> _Raw:
        body = json.loads(request.data.decode()) if request.data else None
        self.sent.append(
            Sent(request.get_method(), request.full_url, dict(request.header_items()), body)
        )
        if not self.replies:
            raise AssertionError(f"no reply queued for {request.full_url}")
        reply = self.replies.pop(0)
        if reply.status >= 400:
            headers = Message()
            for name, value in reply.headers.items():
                headers[name] = value
            data = b"" if reply.body is None else json.dumps(reply.body).encode()
            raise urllib.error.HTTPError(
                request.full_url, reply.status, "error", headers, io.BytesIO(data)
            )
        return _Raw(reply)


def project(**overrides: Any) -> Project:
    raw: dict[str, Any] = {
        "project": "test-app",
        "window_days": 7,
        "impact_days": 7,
        "baseline": {"since": "2026-08-01", "until": "2026-08-07"},
        "journeys": [
            {
                "id": "load",
                "name": "Page load",
                "unit": "ms",
                "target": 600,
                "weight": 2,
                "source": {"kind": "datadog-metric", "query": "p75:app.load{env:prod}"},
            },
            {
                "id": "throughput",
                "name": "Messages per second",
                "unit": "ops",
                "direction": "higher",
                "target": 400,
                "source": {"kind": "file"},
            },
        ],
        "benchmarks": [
            {
                "id": "tree",
                "name": "Tree build",
                "command": ["node", "bench.js"],
                "journeys": ["load"],
                "ceiling": 1000,
                "original": 2000,
            }
        ],
    }
    raw.update(overrides)
    return parse_project(raw)


def steps(
    start: date, days: int, levels: list[tuple[int, float]], wobble: float = 0.0
) -> list[Point]:
    """Daily points: `levels` is (day index from which it applies, value); a small sawtooth."""
    points = []
    for i in range(days):
        value = next(v for start_index, v in reversed(levels) if i >= start_index)
        points.append(Point(start + timedelta(days=i), value * (1 + wobble * ((i % 3) - 1))))
    return points
