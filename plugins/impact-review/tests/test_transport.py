import logging

import pytest
from conftest import TOKEN, FakeGitHub, Reply, fixture, transport_for
from impact_review.connectors.github.errors import AuthError, GitHubError, NetworkError, SsoError


def test_graphql_posts_query_with_bearer_token_and_api_headers() -> None:
    fake = FakeGitHub().on("Viewer", Reply(body=fixture("viewer")))
    data, warnings = transport_for(fake).graphql("query Viewer { viewer { login } }", {})
    assert data["viewer"]["login"] == "jdean"
    assert warnings == []
    sent = fake.sent[0]
    assert sent.method == "POST"
    assert sent.url == "https://api.github.com/graphql"
    assert sent.headers["Authorization"] == f"Bearer {TOKEN}"
    assert sent.headers["X-github-api-version"] == "2022-11-28"
    assert sent.headers["User-agent"].startswith("impact-review/")


def test_mutations_are_refused_before_any_request() -> None:
    fake = FakeGitHub()
    with pytest.raises(GitHubError, match="read-only"):
        transport_for(fake).graphql("mutation { addStar(input: {}) { clientMutationId } }", {})
    assert fake.sent == []


def test_plain_http_is_refused() -> None:
    fake = FakeGitHub()
    transport = transport_for(fake)
    transport.endpoints = transport.endpoints.__class__("x", "http://x/graphql", "http://x")
    with pytest.raises(GitHubError, match="non-https"):
        transport.graphql("query A { viewer { login } }", {})
    assert fake.sent == []


def test_partial_data_returns_errors_as_warnings() -> None:
    fake = FakeGitHub().on("Commits", Reply(body=fixture("partial_error")))
    data, warnings = transport_for(fake).graphql("query Commits { x }", {})
    assert data["repository"]["defaultBranchRef"]["name"] == "main"
    assert warnings == ["Field 'changedFilesIfAvailable' doesn't exist on type 'Commit'"]


def test_saml_error_in_graphql_body_becomes_sso_error() -> None:
    fake = FakeGitHub().on("Viewer", Reply(body=fixture("sso_error")))
    with pytest.raises(SsoError, match="organization acme requires SSO"):
        transport_for(fake).graphql("query Viewer { viewer { login } }", {})


def test_sso_header_on_403_names_the_authorization_url() -> None:
    fake = FakeGitHub().on(
        "Viewer",
        Reply(
            status=403,
            body={"message": "forbidden"},
            headers={"X-GitHub-SSO": "required; url=https://github.com/orgs/acme/sso?x=1"},
        ),
    )
    with pytest.raises(SsoError, match="https://github.com/orgs/acme/sso"):
        transport_for(fake).graphql("query Viewer { viewer { login } }", {})


def test_401_is_an_auth_error_without_retry() -> None:
    fake = FakeGitHub().on("Viewer", Reply(status=401, body={"message": "Bad credentials"}))
    with pytest.raises(AuthError, match="401"):
        transport_for(fake).graphql("query Viewer { viewer { login } }", {})
    assert len(fake.sent) == 1


def test_secondary_rate_limit_waits_retry_after_then_succeeds() -> None:
    fake = FakeGitHub().on(
        "Viewer",
        Reply(status=403, body={"message": "slow down"}, headers={"Retry-After": "7"}),
        Reply(body=fixture("viewer")),
        Reply(body=fixture("viewer")),
    )
    data, _ = transport_for(fake).graphql("query Viewer { viewer { login } }", {})
    assert data["viewer"]["login"] == "jdean"
    assert fake.sleeps == [7.0]
    assert len(fake.sent) == 2


def test_server_errors_back_off_exponentially_then_give_up() -> None:
    fake = FakeGitHub().on("Viewer", Reply(status=502, body={"message": "bad gateway"}))
    with pytest.raises(GitHubError, match="HTTP 502"):
        transport_for(fake).graphql("query Viewer { viewer { login } }", {})
    assert fake.sleeps == [2.0, 4.0, 8.0]
    assert len(fake.sent) == 4


def test_network_failure_is_a_network_error(caplog: pytest.LogCaptureFixture) -> None:
    import urllib.error

    def opener(request: object, timeout: float) -> object:
        raise urllib.error.URLError("connection refused")

    transport = transport_for(FakeGitHub())
    transport.opener = opener
    transport.sleeper = lambda _s: None
    with (
        caplog.at_level(logging.WARNING),
        pytest.raises(NetworkError, match="cannot reach github.com"),
    ):
        transport.graphql("query Viewer { viewer { login } }", {})
    assert TOKEN not in caplog.text


def test_rest_get_returns_status_and_body_and_passes_202_through() -> None:
    fake = FakeGitHub().on("repos/acme/api/stats/contributors", Reply(status=202), Reply(body=[1]))
    transport = transport_for(fake)
    first = transport.rest_get("/repos/acme/api/stats/contributors")
    second = transport.rest_get("repos/acme/api/stats/contributors")
    assert (first.status, first.body) == (202, {})
    assert (second.status, second.body) == (200, [1])
    assert fake.sent[0].url == "https://api.github.com/repos/acme/api/stats/contributors"


def test_enterprise_server_paths() -> None:
    fake = FakeGitHub().on("Viewer", Reply(body=fixture("viewer")))
    fake.on("repos/acme/api/stats/contributors", Reply(body=[]))
    transport = transport_for(fake, "ghe.corp.example")
    transport.graphql("query Viewer { viewer { login } }", {})
    transport.rest_get("repos/acme/api/stats/contributors")
    assert fake.sent[0].url == "https://ghe.corp.example/api/graphql"
    assert fake.sent[1].url == "https://ghe.corp.example/api/v3/repos/acme/api/stats/contributors"
