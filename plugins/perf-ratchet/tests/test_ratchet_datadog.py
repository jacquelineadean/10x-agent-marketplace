import logging
from datetime import date

import pytest
from perf_ratchet.connectors.datadog.sites import api_url
from perf_ratchet.connectors.datadog.source import DatadogSource, datadog_transport
from perf_ratchet.connectors.errors import AuthError, NetworkError, SourceError
from perf_ratchet.core.model import Point, Window
from ratchet_helpers import API_KEY, APP_KEY, FakeHttp, Reply, fixture, project

WINDOW = Window(date(2025, 10, 6), date(2025, 10, 9))


def _source(fake: FakeHttp, recorded: dict[str, object] | None = None) -> DatadogSource:
    transport = datadog_transport("https://api.datadoghq.com", API_KEY, APP_KEY)
    transport.opener, transport.sleeper = fake, fake.sleep
    keep = None if recorded is None else recorded.__setitem__
    return DatadogSource(transport, keep)


def _rum_project():  # type: ignore[no-untyped-def]
    return project(
        journeys=[
            {
                "id": "load",
                "source": {
                    "kind": "datadog-rum",
                    "query": "@type:view",
                    "measure": "@view.loading_time",
                    "scale": 1e-6,
                },
            }
        ],
        benchmarks=[],
    )


def test_metric_query_is_a_get_with_both_keys_and_daily_medians() -> None:
    fake = FakeHttp(Reply(body=fixture("datadog_metric.json")))
    recorded: dict[str, object] = {}
    series = _source(fake, recorded).fetch(project().journey("load"), WINDOW)
    sent = fake.sent[0]
    assert sent.method == "GET"
    assert sent.url.startswith(
        "https://api.datadoghq.com/api/v1/query?from=1759708800&to=1760054399"
    )
    assert "query=p75%3Aapp.load%7Benv%3Aprod%7D" in sent.url
    assert sent.headers["Dd-api-key"] == API_KEY
    assert sent.headers["Dd-application-key"] == APP_KEY
    assert series.points == (
        Point(date(2025, 10, 6), 220.0),
        Point(date(2025, 10, 7), 200.0),
        Point(date(2025, 10, 8), 193.0),
        Point(date(2025, 10, 9), 182.0),
    )
    assert list(recorded) == ["datadog-load-2025-10-06_2025-10-09"]


def test_grouped_metric_queries_warn_and_use_the_first_series() -> None:
    fake = FakeHttp(Reply(body=fixture("datadog_metric_grouped.json")))
    series = _source(fake).fetch(project().journey("load"), WINDOW)
    assert series.points[0].value == 100.0
    assert "2 series" in series.warnings[0]


def test_a_query_error_names_the_journey() -> None:
    fake = FakeHttp(Reply(body=fixture("datadog_metric_error.json")))
    with pytest.raises(SourceError, match="load: Datadog query failed: Error parsing query"):
        _source(fake).fetch(project().journey("load"), WINDOW)


def test_rum_aggregation_posts_a_read_only_query_and_scales_nanoseconds() -> None:
    fake = FakeHttp(Reply(body=fixture("datadog_rum.json")))
    p = _rum_project()
    series = _source(fake).fetch(p.journey("load"), WINDOW)
    sent = fake.sent[0]
    assert sent.method == "POST"
    assert sent.url == "https://api.datadoghq.com/api/v2/rum/analytics/aggregate"
    assert sent.body["compute"] == [
        {
            "aggregation": "pc75",
            "metric": "@view.loading_time",
            "type": "timeseries",
            "interval": "1d",
        }
    ]
    assert sent.body["filter"] == {
        "from": "2025-10-06T00:00:00Z",
        "to": "2025-10-09T23:59:59Z",
        "query": "@type:view",
    }
    assert [p.value for p in series.points] == [812.0, 798.0, 640.5]


def test_posts_to_any_other_path_are_refused_before_sending() -> None:
    fake = FakeHttp()
    source = _source(fake)
    with pytest.raises(SourceError, match="only reads"):
        source.transport.post_query("/api/v1/monitor", {"name": "x"})
    assert fake.sent == []


def test_plain_http_is_refused() -> None:
    fake = FakeHttp()
    source = _source(fake)
    source.transport.base_url = "http://api.datadoghq.com"
    with pytest.raises(SourceError, match="non-https"):
        source.fetch(project().journey("load"), WINDOW)
    assert fake.sent == []


def test_rejected_keys_raise_auth_error_without_the_keys(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeHttp(Reply(status=403, body=fixture("datadog_forbidden.json")))
    with pytest.raises(AuthError) as error:
        _source(fake).fetch(project().journey("load"), WINDOW)
    assert "HTTP 403" in str(error.value)
    assert API_KEY not in str(error.value) and APP_KEY not in caplog.text


def test_rate_limits_wait_for_the_reset_then_succeed(caplog: pytest.LogCaptureFixture) -> None:
    fake = FakeHttp(
        Reply(
            status=429, body={"errors": ["Too many requests"]}, headers={"X-RateLimit-Reset": "7"}
        ),
        Reply(body=fixture("datadog_metric.json")),
    )
    with caplog.at_level(logging.WARNING):
        series = _source(fake).fetch(project().journey("load"), WINDOW)
    assert fake.sleeps == [7.0]
    assert len(series.points) == 4
    assert "query=" not in caplog.text and API_KEY not in caplog.text


def test_server_errors_back_off_then_give_up() -> None:
    fake = FakeHttp(*[Reply(status=503)] * 4)
    with pytest.raises(SourceError, match="HTTP 503"):
        _source(fake).fetch(project().journey("load"), WINDOW)
    assert fake.sleeps == [2.0, 4.0, 8.0]


def test_network_failures_become_network_errors() -> None:
    import urllib.error

    def broken(request: object, timeout: float) -> object:
        raise urllib.error.URLError("no route")

    source = _source(FakeHttp())
    source.transport.opener = broken
    source.transport.sleeper = lambda _: None
    with pytest.raises(NetworkError, match="cannot reach Datadog"):
        source.fetch(project().journey("load"), WINDOW)


@pytest.mark.parametrize(
    ("site", "url"),
    [
        ("datadoghq.com", "https://api.datadoghq.com"),
        ("us5.datadoghq.com", "https://api.us5.datadoghq.com"),
        ("datadoghq.eu", "https://api.datadoghq.eu"),
        ("app.datadoghq.eu", "https://api.datadoghq.eu"),
        ("ddog-gov.com", "https://api.ddog-gov.com"),
        ("", "https://api.datadoghq.com"),
    ],
)
def test_sites_map_to_api_hosts(site: str, url: str) -> None:
    assert api_url(site) == url


def test_keys_are_never_sent_to_a_host_that_is_not_datadog() -> None:
    with pytest.raises(ValueError, match="not a Datadog site"):
        api_url("datadoghq.com.attacker.example")
