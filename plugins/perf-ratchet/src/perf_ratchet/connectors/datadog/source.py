"""Every Datadog call: metric timeseries (GET) and RUM aggregation (a read-only POST query)."""

from __future__ import annotations

import logging
from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any

from perf_ratchet.connectors.errors import SourceError
from perf_ratchet.connectors.http import JsonTransport
from perf_ratchet.core.model import Journey, Series, Window
from perf_ratchet.core.records import daily

log = logging.getLogger(__name__)

METRICS_PATH = "/api/v1/query"
RUM_PATH = "/api/v2/rum/analytics/aggregate"
READ_ONLY_POSTS = frozenset({RUM_PATH})

Recorder = Callable[[str, Any], None]


def datadog_transport(site_url: str, api_key: str, app_key: str) -> JsonTransport:
    return JsonTransport(
        name="Datadog",
        base_url=site_url,
        headers={"DD-API-KEY": api_key, "DD-APPLICATION-KEY": app_key},
        read_only_posts=READ_ONLY_POSTS,
    )


class DatadogSource:
    def __init__(self, transport: JsonTransport, record: Recorder | None = None) -> None:
        self.transport = transport
        self.record = record

    def fetch(self, journey: Journey, window: Window) -> Series:
        if journey.source.kind == "datadog-metric":
            return self._metric(journey, window)
        if journey.source.kind == "datadog-rum":
            return self._rum(journey, window)
        raise SourceError(f"{journey.id}: Datadog cannot fetch a {journey.source.kind} source")

    def _metric(self, journey: Journey, window: Window) -> Series:
        start, end = _bounds(window)
        body = self.transport.get(
            METRICS_PATH,
            {
                "from": str(int(start.timestamp())),
                "to": str(int(end.timestamp())),
                "query": journey.source.query,
            },
        )
        self._keep(journey.id, window, body)
        if not isinstance(body, dict) or body.get("status") == "error":
            raise SourceError(f"{journey.id}: Datadog query failed: {_message(body)}")
        series = body.get("series") or []
        warnings: list[str] = []
        if not series:
            warnings.append(f"{journey.id}: the Datadog query returned no series")
            return Series(journey.id, (), _label(journey), tuple(warnings))
        if len(series) > 1:
            warnings.append(
                f"{journey.id}: the query returned {len(series)} series; using the first. "
                "Aggregate across groups so it returns one."
            )
        pairs = [
            (point[0] / 1000, point[1])
            for point in series[0].get("pointlist") or []
            if isinstance(point, list) and len(point) == 2 and point[1] is not None
        ]
        return Series(
            journey.id, daily(pairs, journey.source.scale), _label(journey), tuple(warnings)
        )

    def _rum(self, journey: Journey, window: Window) -> Series:
        start, end = _bounds(window)
        query = {
            "compute": [
                {
                    "aggregation": journey.source.aggregation,
                    "metric": journey.source.measure,
                    "type": "timeseries",
                    "interval": "1d",
                }
            ],
            "filter": {
                "from": start.isoformat().replace("+00:00", "Z"),
                "to": end.isoformat().replace("+00:00", "Z"),
                "query": journey.source.query,
            },
        }
        body = self.transport.post_query(RUM_PATH, query)
        self._keep(journey.id, window, body)
        buckets = (
            ((body or {}).get("data") or {}).get("buckets") if isinstance(body, dict) else None
        )
        if not buckets:
            return Series(
                journey.id, (), _label(journey), (f"{journey.id}: RUM returned no buckets",)
            )
        computes = (buckets[0].get("computes") or {}).get("c0") or []
        pairs = [
            (_epoch(item["time"]), item["value"])
            for item in computes
            if isinstance(item, dict) and item.get("value") is not None and "time" in item
        ]
        return Series(journey.id, daily(pairs, journey.source.scale), _label(journey))

    def _keep(self, journey_id: str, window: Window, body: Any) -> None:
        if self.record is not None:
            self.record(f"datadog-{journey_id}-{window.since}_{window.until}", body)


def _bounds(window: Window) -> tuple[datetime, datetime]:
    start = datetime.combine(window.since, time.min, tzinfo=UTC)
    end = datetime.combine(window.until + timedelta(days=1), time.min, tzinfo=UTC) - timedelta(
        seconds=1
    )
    return start, end


def _epoch(value: Any) -> float:
    if isinstance(value, int | float):
        return float(value) / (1000 if value > 1e11 else 1)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()


def _label(journey: Journey) -> str:
    source = journey.source
    if source.kind == "datadog-rum":
        return f"Datadog RUM {source.aggregation}({source.measure}) where {source.query}"
    return f"Datadog metric {source.query}"


def _message(body: Any) -> str:
    if isinstance(body, dict):
        return str(body.get("error") or body.get("errors") or "unknown error")[:300]
    return "unexpected response"
