"""PagerDuty for the script lane: incidents counted per period.

One GET per period asks for one incident and the total. PagerDuty lists at most six
months at a time, so a longer period is counted month by month and added up.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.http import JsonTransport
from sources.connectors.wire import Wire
from sources.core.collect import RequestError, Result, measured, only, per
from sources.core.periods import Window, periods
from sources.core.reach import Reach

API = "https://api.pagerduty.com"
FILTERS = {
    "service_ids": re.compile(r"^[A-Z0-9]{1,20}$"),
    "team_ids": re.compile(r"^[A-Z0-9]{1,20}$"),
    "urgencies": re.compile(r"^(high|low)$"),
    "statuses": re.compile(r"^(triggered|acknowledged|resolved)$"),
}
LONGEST_DAYS = 180


def _filters(raw: Any) -> dict[str, list[str]]:
    if not isinstance(raw, Mapping):
        raise RequestError("request.incidents must be an object of filters, {} for every one")
    out = {}
    for key, values in raw.items():
        pattern = FILTERS.get(str(key))
        if pattern is None:
            raise RequestError(f"request.incidents.{key} is unknown; use {', '.join(FILTERS)}")
        if not isinstance(values, list) or not all(
            isinstance(v, str) and pattern.match(v) for v in values
        ):
            raise RequestError(f"request.incidents.{key} must be a list such as the API takes")
        out[f"{key}[]"] = list(values)
    return out


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"incidents"})
    if "incidents" not in request:
        raise RequestError("a pagerduty request needs incidents")
    filters = _filters(request["incidents"])
    every = per(request)
    (token,) = reach.need("token")
    transport = JsonTransport(
        "PagerDuty",
        reach.url() if reach.host else API,
        {
            "Authorization": f"Token token={token}",
            "Accept": "application/vnd.pagerduty+json;version=2",
        },
        opener=wire.opener,
        sleeper=wire.sleeper,
    )

    def total(w: Window) -> int:
        params = {"since": w.start.isoformat(), "until": w.until.isoformat(), "time_zone": "UTC"}
        body = transport.get("/incidents", {**params, **filters, "total": "true", "limit": 1})
        if not isinstance(body, Mapping) or not isinstance(body.get("total"), int):
            raise SourceError("PagerDuty answered without a total")
        return int(body["total"])

    def count(w: Window) -> int:
        if (w.end - w.start).days < LONGEST_DAYS:
            return total(w)
        return sum(total(p.window) for p in periods(w, "month"))

    value, table = measured(span, every, "count", count)
    shown = " ".join(f"{k}={','.join(v)}" for k, v in filters.items())
    suffix = f" per {every}" if every else ""
    query = f"GET /incidents since={span.start} until={span.until} {shown}".strip() + suffix
    return Result(query, value, table)
