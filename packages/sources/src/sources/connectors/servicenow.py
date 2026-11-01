"""ServiceNow for the script lane: record counts and averages from the Aggregate API.

One GET per period to `/api/now/stats/<table>` returns the count, and the average of a
field when the request names one; no record leaves the instance.
"""

from __future__ import annotations

import base64
import re
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.http import JsonTransport
from sources.connectors.wire import Wire
from sources.core.collect import Number, RequestError, Result, field_name, measured, only, per, text
from sources.core.periods import Window
from sources.core.reach import Reach

TABLE = re.compile(r"^[a-z][a-z0-9_]{0,79}$")


def _base(reach: Reach) -> str:
    raw = (reach.host or reach.key("url")).strip().rstrip("/")
    name = raw.removeprefix("https://")
    if name and "." not in name:
        return f"https://{name}.service-now.com"
    return reach.url()


def _auth(reach: Reach) -> dict[str, str]:
    if reach.key("token"):
        return {"Authorization": f"Bearer {reach.key('token')}"}
    user, password = reach.need("user", "password")
    return {"Authorization": "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode()}


def _within(query: str, date: str, w: Window) -> str:
    """The encoded query limited to the window, in the form ServiceNow's own lists write."""
    span = (
        f"{date}BETWEENjavascript:gs.dateGenerate('{w.start.isoformat()}','00:00:00')"
        f"@javascript:gs.dateGenerate('{w.end.isoformat()}','23:59:59')"
    )
    return f"{query}^{span}" if query else span


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"table", "query", "date", "avg"})
    table = text(request, "table", 80)
    if not TABLE.match(table):
        raise RequestError("request.table must be a table name such as incident")
    query = text(request, "query", 1000, required=False)
    date = field_name(request, "date", "opened_at")
    average = field_name(request, "avg", "calendar_stc") if "avg" in request else ""
    every = per(request)
    transport = JsonTransport(
        "ServiceNow", _base(reach), _auth(reach), opener=wire.opener, sleeper=wire.sleeper
    )

    def stats(w: Window) -> Number:
        params = {"sysparm_query": _within(query, date, w), "sysparm_count": "true"}
        if average:
            params["sysparm_avg_fields"] = average
        body = transport.get(f"/api/now/stats/{table}", params)
        found = body.get("result", {}).get("stats") if isinstance(body, Mapping) else None
        if not isinstance(found, Mapping) or "count" not in found:
            raise SourceError("ServiceNow answered without stats")
        if not average:
            return int(found["count"])
        mean = (found.get("avg") or {}).get(average)
        return float(mean) if mean not in (None, "") else None

    name = f"avg_{average}" if average else "count"
    value, result = measured(span, every, name, stats)
    measure = f"&sysparm_avg_fields={average}" if average else "&sysparm_count=true"
    suffix = f" per {every}" if every else ""
    shown = f"GET /api/now/stats/{table}?sysparm_query={_within(query, date, span)}{measure}"
    return Result(shown + suffix, value, result)
