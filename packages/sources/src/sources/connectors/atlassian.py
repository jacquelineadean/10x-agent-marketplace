"""Jira and Confluence for the script lane: issues and pages counted per period.

Each count asks for the total only. Jira Cloud counts through its read-only
`search/approximate-count` POST; Jira Data Center and Confluence through search GETs.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.http import JsonTransport
from sources.connectors.wire import Wire
from sources.core.collect import Result, choice, field_name, measured, only, per, text
from sources.core.periods import Window
from sources.core.reach import Reach

JIRA_COUNT = "/rest/api/3/search/approximate-count"
ORDER_BY = re.compile(r"\s+order\s+by\s+.*$", re.IGNORECASE | re.DOTALL)


def _transport(reach: Reach, wire: Wire, name: str, base: str) -> JsonTransport:
    email, token = reach.need("email", "token")
    basic = base64.b64encode(f"{email}:{token}".encode()).decode()
    return JsonTransport(
        name,
        base,
        {"Authorization": f"Basic {basic}"},
        read_only_posts=frozenset({JIRA_COUNT}),
        opener=wire.opener,
        sleeper=wire.sleeper,
    )


def _within(clause: str, date: str, w: Window) -> str:
    """The clause limited to the window; JQL and CQL share the date syntax."""
    core = ORDER_BY.sub("", clause).strip()
    return f'({core}) AND {date} >= "{w.start.isoformat()}" AND {date} < "{w.until.isoformat()}"'


def _number(body: Any, key: str, name: str) -> int:
    if not isinstance(body, Mapping) or not isinstance(body.get(key), int):
        raise SourceError(f"{name} answered without a {key}")
    return int(body[key])


def jira(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"jql", "date"})
    jql = text(request, "jql", 1000)
    date = field_name(request, "date", "created")
    every = per(request)
    base = reach.url()
    transport = _transport(reach, wire, "Jira", base)
    cloud = base.split("/")[2].endswith(".atlassian.net")

    def count(w: Window) -> int:
        clause = _within(jql, date, w)
        if cloud:
            return _number(transport.post_query(JIRA_COUNT, {"jql": clause}), "count", "Jira")
        body = transport.get("/rest/api/2/search", {"jql": clause, "maxResults": 0, "fields": "id"})
        return _number(body, "total", "Jira")

    value, table = measured(span, every, "count", count)
    suffix = f" per {every}" if every else ""
    return Result(f"JQL {_within(jql, date, span)}{suffix}", value, table)


def confluence(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"cql", "date"})
    cql = text(request, "cql", 1000)
    date = choice(request, "date", ("created", "lastmodified"), "created")
    every = per(request)
    base = reach.url()
    if base.split("/")[2].endswith(".atlassian.net") and not base.endswith("/wiki"):
        base += "/wiki"
    transport = _transport(reach, wire, "Confluence", base)

    def count(w: Window) -> int:
        body = transport.get("/rest/api/search", {"cql": _within(cql, date, w), "limit": 1})
        return _number(body, "totalSize", "Confluence")

    value, table = measured(span, every, "count", count)
    suffix = f" per {every}" if every else ""
    return Result(f"CQL {_within(cql, date, span)}{suffix}", value, table)
