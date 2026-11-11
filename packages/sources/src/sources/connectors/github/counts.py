"""GitHub for the script lane: search results and workflow runs, counted per period.

Each count is one GET that asks for a single item and reads the total, so no item ever
leaves GitHub. Search allows 30 requests a minute; the transport waits out the limit.
"""

from __future__ import annotations

import re
import urllib.parse
from collections.abc import Mapping
from typing import Any

from sources.connectors.github.errors import GitHubError
from sources.connectors.github.hosts import endpoints_for
from sources.connectors.github.http import GitHubTransport
from sources.connectors.github.token import resolve_token
from sources.connectors.wire import Wire
from sources.core.collect import RequestError, Result, choice, measured, only, per, text
from sources.core.periods import Window
from sources.core.reach import Reach

DATES = ("created", "merged", "closed", "updated")
STATUSES = ("success", "failure", "completed", "any")
REPO = re.compile(r"^[A-Za-z0-9_.-]{1,39}/[A-Za-z0-9_.-]{1,100}$")
WORKFLOW = re.compile(r"^[A-Za-z0-9_.-]{1,120}$")


def _total(transport: GitHubTransport, path: str, warnings: list[str]) -> int:
    response = transport.rest_get(path)
    body = response.body if isinstance(response.body, Mapping) else {}
    if response.status != 200 or "total_count" not in body:
        raise GitHubError(f"GitHub answered HTTP {response.status} without a total")
    if body.get("incomplete_results"):
        warnings.append("GitHub search timed out on part of the index; a count may be low")
    return int(body["total_count"])


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"search", "date", "runs", "workflow", "status", "branch"})
    every = per(request)
    endpoints = endpoints_for(reach.host or "github.com")
    known = {"GITHUB_TOKEN": reach.key("token")} if reach.key("token") else {}
    transport = GitHubTransport(
        endpoints,
        resolve_token(known, endpoints.host, wire.gh_token),
        opener=wire.opener,
        sleeper=wire.sleeper,
    )
    warnings: list[str] = []
    suffix = f" per {every}" if every else ""
    if "search" in request:
        search = text(request, "search", 256)
        date = choice(request, "date", DATES, "created")
        if re.search(rf"\b{date}:", search):
            raise RequestError(f"request.search filters {date}: itself; the window sets it")

        def found(w: Window) -> int:
            q = urllib.parse.urlencode({"q": f"{search} {date}:{w.text()}", "per_page": "1"})
            return _total(transport, f"search/issues?{q}", warnings)

        value, table = measured(span, every, "count", found)
        query = f'search/issues q="{search} {date}:{span.text()}"{suffix}'
        return Result(query, value, table, warnings)
    if "runs" not in request:
        raise RequestError("a github request needs search or runs")
    repo = text(request, "runs", 140)
    if not REPO.match(repo):
        raise RequestError("request.runs must be owner/repo")
    workflow = text(request, "workflow", 120, required=False)
    if workflow and not WORKFLOW.match(workflow):
        raise RequestError("request.workflow must be a workflow file name or id")
    status = choice(request, "status", STATUSES, "success")
    branch = text(request, "branch", 120, required=False)
    path = f"repos/{repo}/actions/" + (f"workflows/{workflow}/runs" if workflow else "runs")
    filters = {"status": status} if status != "any" else {}
    if branch:
        filters["branch"] = branch

    def runs(w: Window) -> int:
        q = urllib.parse.urlencode({"created": w.text(), **filters, "per_page": "1"})
        return _total(transport, f"{path}?{q}", warnings)

    value, table = measured(span, every, "count", runs)
    shown = urllib.parse.urlencode({"created": span.text(), **filters})
    return Result(f"GET {path}?{shown}{suffix}", value, table, warnings)
