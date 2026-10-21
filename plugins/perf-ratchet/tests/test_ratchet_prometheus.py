from datetime import date

import pytest
from perf_ratchet.connectors.prometheus.source import PrometheusSource, prometheus_transport
from perf_ratchet.core.model import Window
from ratchet_helpers import FakeHttp, Reply, fixture, project

WINDOW = Window(date(2025, 10, 6), date(2025, 10, 9))


def _journey():  # type: ignore[no-untyped-def]
    p = project(
        journeys=[
            {
                "id": "api",
                "source": {
                    "kind": "prometheus",
                    "query": "histogram_quantile(0.75, x)",
                    "scale": 1000,
                },
            }
        ],
        benchmarks=[],
    )
    return p.journey("api")


def test_range_query_steps_one_day_and_scales_seconds_to_ms() -> None:
    fake = FakeHttp(Reply(body=fixture("prometheus_range.json")))
    transport = prometheus_transport("https://prom.example", "tok")
    transport.opener = fake
    series = PrometheusSource(transport).fetch(_journey(), WINDOW)
    sent = fake.sent[0]
    assert sent.url.startswith("https://prom.example/api/v1/query_range?query=histogram_quantile")
    assert "step=86400" in sent.url
    assert sent.headers["Authorization"] == "Bearer tok"
    assert [round(p.value, 1) for p in series.points] == [214.0, 209.0, 198.0]


def test_plain_http_only_on_localhost_and_never_with_a_token() -> None:
    with pytest.raises(ValueError, match="https"):
        prometheus_transport("http://prom.internal:9090", None)
    with pytest.raises(ValueError, match="plain http"):
        prometheus_transport("http://localhost:9090", "tok")
    assert prometheus_transport("http://localhost:9090", None).allow_plain_http


def test_failed_queries_name_the_journey() -> None:
    fake = FakeHttp(Reply(body={"status": "error", "error": "parse error"}))
    transport = prometheus_transport("https://prom.example", None)
    transport.opener = fake
    with pytest.raises(RuntimeError, match="api: Prometheus query failed: parse error"):
        PrometheusSource(transport).fetch(_journey(), WINDOW)
