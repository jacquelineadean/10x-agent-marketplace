"""Every Prometheus call: one range query per journey, one step per day."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, time, timedelta
from typing import Any
from urllib.parse import urlparse

from perf_ratchet.connectors.errors import SourceError
from perf_ratchet.connectors.http import JsonTransport
from perf_ratchet.core.model import Journey, Series, Window
from perf_ratchet.core.records import daily

QUERY_RANGE = "/api/v1/query_range"
DAY_SECONDS = 86_400
_LOCAL = ("localhost", "127.0.0.1", "::1")

Recorder = Callable[[str, Any], None]


def prometheus_transport(url: str, token: str | None) -> JsonTransport:
    """https anywhere; plain http only to this machine, and never with a token."""
    host = urlparse(url).hostname or ""
    local_http = url.startswith("http://") and host in _LOCAL
    if url.startswith("http://") and not local_http:
        raise ValueError("Prometheus URL must use https unless it is on localhost")
    if local_http and token:
        raise ValueError("refusing to send PROMETHEUS_TOKEN over plain http")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    return JsonTransport(
        name="Prometheus", base_url=url, headers=headers, allow_plain_http=local_http
    )


class PrometheusSource:
    """Evaluates the query at the midnight that ends each day, and files the value under the day
    that just ended, so a `[1d]` range vector at D+1 00:00 counts as day D."""

    def __init__(self, transport: JsonTransport, record: Recorder | None = None) -> None:
        self.transport = transport
        self.record = record

    def fetch(self, journey: Journey, window: Window) -> Series:
        start = datetime.combine(window.since + timedelta(days=1), time.min, tzinfo=UTC)
        end = datetime.combine(window.until + timedelta(days=1), time.min, tzinfo=UTC)
        body = self.transport.get(
            QUERY_RANGE,
            {
                "query": journey.source.query,
                "start": str(int(start.timestamp())),
                "end": str(int(end.timestamp())),
                "step": str(DAY_SECONDS),
            },
        )
        if self.record is not None:
            self.record(f"prometheus-{journey.id}-{window.since}_{window.until}", body)
        if not isinstance(body, dict) or body.get("status") != "success":
            detail = body.get("error", "unexpected response") if isinstance(body, dict) else ""
            raise SourceError(f"{journey.id}: Prometheus query failed: {detail}")
        results = (body.get("data") or {}).get("result") or []
        if not results:
            return Series(journey.id, (), _label(journey), (f"{journey.id}: no Prometheus series",))
        warnings: tuple[str, ...] = ()
        if len(results) > 1:
            warnings = (f"{journey.id}: {len(results)} series returned; using the first",)
        pairs = []
        for stamp, raw in results[0].get("values") or []:
            try:
                pairs.append((float(stamp) - 1, float(raw)))
            except (TypeError, ValueError):
                continue
        return Series(journey.id, daily(pairs, journey.source.scale), _label(journey), warnings)


def _label(journey: Journey) -> str:
    return f"Prometheus {journey.source.query}"
