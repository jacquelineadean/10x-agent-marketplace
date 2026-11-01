"""Datadog for the script lane: metrics, SLO history and RUM, reduced per period.

Metrics come back as daily rollups from one GET, and code reduces the days in each
period: `sum` adds them, `avg` averages them, `max` and `min` take the extreme, `last`
takes the final day. SLO history is one GET per period. RUM computes each period's value
in Datadog through its read-only aggregate POST, so percentiles stay exact.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import UTC, date, datetime, time
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.http import JsonTransport
from sources.connectors.wire import Wire
from sources.core.collect import Number, RequestError, Result, choice, measured, only, per, text
from sources.core.periods import Window
from sources.core.reach import Reach, ReachError

METRICS = "/api/v1/query"
RUM = "/api/v2/rum/analytics/aggregate"
SITE = re.compile(r"^(?:[a-z0-9-]+\.)?(?:datadoghq\.com|datadoghq\.eu|ddog-gov\.com)$")
REDUCE = ("avg", "sum", "max", "min", "last")
AGGREGATIONS = (
    "count",
    "cardinality",
    "pc75",
    "pc90",
    "pc95",
    "pc98",
    "pc99",
    "sum",
    "min",
    "max",
    "avg",
    "median",
)
SLO = re.compile(r"^[A-Za-z0-9]{1,64}$")


def api_url(site: str) -> str:
    """`datadoghq.com` becomes `https://api.datadoghq.com`; keys go only to these hosts."""
    host = (site or "datadoghq.com").strip().lower().removeprefix("https://")
    host = host.removeprefix("api.").removeprefix("app.").rstrip("/")
    if not SITE.match(host):
        raise ReachError(f"{site!r} is not a Datadog site, such as datadoghq.com or datadoghq.eu")
    return f"https://api.{host}"


def _epoch(day: date) -> int:
    return int(datetime.combine(day, time.min, tzinfo=UTC).timestamp())


def _days(transport: JsonTransport, query: str, span: Window) -> dict[date, float]:
    body = transport.get(
        METRICS, {"from": _epoch(span.start), "to": _epoch(span.until) - 1, "query": query}
    )
    if not isinstance(body, Mapping) or body.get("status") == "error":
        detail = body.get("error") if isinstance(body, Mapping) else ""
        raise SourceError(f"the Datadog query failed: {str(detail)[:200]}")
    series = body.get("series") or []
    if len(series) > 1:
        raise SourceError(
            f"the Datadog query returned {len(series)} series; aggregate across groups"
        )
    days: dict[date, float] = {}
    points = series[0].get("pointlist") if series else None
    for point in points or []:
        if isinstance(point, list) and len(point) == 2 and point[1] is not None:
            days[datetime.fromtimestamp(point[0] / 1000, UTC).date()] = float(point[1])
    return days


def _reduce(values: list[float], how: str) -> Number:
    if not values:
        return None
    if how == "sum":
        return sum(values)
    if how == "max":
        return max(values)
    if how == "min":
        return min(values)
    if how == "last":
        return values[-1]
    return sum(values) / len(values)


def _total(body: Any) -> Number:
    buckets = (body.get("data") or {}).get("buckets") if isinstance(body, Mapping) else None
    if not buckets:
        return None
    value = (buckets[0].get("computes") or {}).get("c0")
    return float(value) if isinstance(value, int | float) else None


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"metric", "reduce", "slo", "rum", "measure", "aggregation"})
    api_key, app_key = reach.need("api_key", "app_key")
    transport = JsonTransport(
        "Datadog",
        api_url(reach.host or reach.key("site")),
        {"DD-API-KEY": api_key, "DD-APPLICATION-KEY": app_key},
        read_only_posts=frozenset({RUM}),
        opener=wire.opener,
        sleeper=wire.sleeper,
    )
    every = per(request)
    suffix = f" per {every}" if every else ""
    if "metric" in request:
        metric = text(request, "metric", 500)
        if ".rollup(" in metric:
            raise RequestError("request.metric must leave out .rollup(); the collector adds it")
        how = choice(request, "reduce", REDUCE, "avg")
        query = f"{metric}.rollup({'avg' if how == 'last' else how}, 86400)"
        days = _days(transport, query, span)

        def reduced(w: Window) -> Number:
            return _reduce([v for d, v in sorted(days.items()) if w.start <= d <= w.end], how)

        value, table = measured(span, every, how, reduced)
        return Result(f"{query} {span.text()}, {how} of days{suffix}", value, table)
    if "slo" in request:
        slo = text(request, "slo", 64)
        if not SLO.match(slo):
            raise RequestError("request.slo must be an SLO id")

        def sli(w: Window) -> Number:
            body = transport.get(
                f"/api/v1/slo/{slo}/history",
                {"from_ts": _epoch(w.start), "to_ts": _epoch(w.until)},
            )
            found = ((body.get("data") or {}).get("overall") or {}).get("sli_value")
            return float(found) if isinstance(found, int | float) else None

        value, table = measured(span, every, "sli", sli)
        return Result(f"GET /api/v1/slo/{slo}/history {span.text()}{suffix}", value, table)
    if "rum" not in request:
        raise RequestError("a datadog request needs metric, slo or rum")
    rum = text(request, "rum", 500)
    aggregation = choice(request, "aggregation", AGGREGATIONS, "pc75")
    measure = text(request, "measure", 120, required=aggregation != "count")
    compute = {
        "aggregation": aggregation,
        "type": "total",
        **({"metric": measure} if measure else {}),
    }

    def total(w: Window) -> Number:
        bounds = {
            "from": f"{w.start.isoformat()}T00:00:00Z",
            "to": f"{w.until.isoformat()}T00:00:00Z",
        }
        return _total(
            transport.post_query(RUM, {"compute": [compute], "filter": {**bounds, "query": rum}})
        )

    value, table = measured(span, every, aggregation, total)
    shown = f"{aggregation}({measure})" if measure else aggregation
    return Result(f"RUM {shown} where {rum} {span.text()}{suffix}", value, table)
