from pathlib import Path

import pytest
from impact_review.config.settings import load_environment, read_dotenv, settings_from
from impact_review.connectors.github.hosts import endpoints_for
from impact_review.connectors.github.token import MissingTokenError, resolve_token


def test_dotenv_reader_skips_comments_and_strips_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# comment\n\nGITHUB_TOKEN=\"abc\"\nIMPACT_REVIEW_HOST='ghe.example.com'\nBAD\n"
    )
    assert read_dotenv(env_file) == {"GITHUB_TOKEN": "abc", "IMPACT_REVIEW_HOST": "ghe.example.com"}


def test_dotenv_never_overrides_a_set_variable(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("GITHUB_TOKEN=from-file\nIMPACT_REVIEW_RUNS=/runs\n")
    merged = load_environment({"GITHUB_TOKEN": "from-process"}, env_file)
    assert merged == {"GITHUB_TOKEN": "from-process", "IMPACT_REVIEW_RUNS": "/runs"}


def test_missing_dotenv_is_fine(tmp_path: Path) -> None:
    assert load_environment({"A": "1"}, tmp_path / ".env") == {"A": "1"}


def test_settings_defaults_and_overrides() -> None:
    defaults = settings_from({})
    assert defaults.host == "github.com"
    assert defaults.runs_root == Path("~/impact-review-runs").expanduser()
    custom = settings_from({"IMPACT_REVIEW_HOST": "ghe.corp", "IMPACT_REVIEW_RUNS": "/runs/r"})
    assert (custom.host, custom.runs_root) == ("ghe.corp", Path("/runs/r"))


@pytest.mark.parametrize(
    ("host", "graphql", "rest"),
    [
        ("github.com", "https://api.github.com/graphql", "https://api.github.com"),
        ("https://GitHub.com/", "https://api.github.com/graphql", "https://api.github.com"),
        (
            "ghe.corp.example",
            "https://ghe.corp.example/api/graphql",
            "https://ghe.corp.example/api/v3",
        ),
        ("octo.ghe.com", "https://api.octo.ghe.com/graphql", "https://api.octo.ghe.com"),
        ("api.octo.ghe.com", "https://api.octo.ghe.com/graphql", "https://api.octo.ghe.com"),
    ],
)
def test_endpoints_per_host_kind(host: str, graphql: str, rest: str) -> None:
    endpoints = endpoints_for(host)
    assert (endpoints.graphql_url, endpoints.rest_url) == (graphql, rest)


@pytest.mark.parametrize("host", ["", "ghe.corp/with/path", "two words"])
def test_bad_hosts_raise(host: str) -> None:
    with pytest.raises(ValueError, match="invalid GitHub host"):
        endpoints_for(host)


def test_token_prefers_github_token_then_gh_token_then_cli() -> None:
    calls: list[str] = []

    def runner(host: str) -> str | None:
        calls.append(host)
        return "cli-token"

    assert resolve_token({"GITHUB_TOKEN": "a", "GH_TOKEN": "b"}, "github.com", runner) == "a"
    assert resolve_token({"GH_TOKEN": "b"}, "github.com", runner) == "b"
    assert resolve_token({"GITHUB_TOKEN": "  "}, "ghe.corp", runner) == "cli-token"
    assert calls == ["ghe.corp"]


def test_missing_token_names_the_fix() -> None:
    with pytest.raises(MissingTokenError, match="gh auth login --hostname ghe.corp"):
        resolve_token({}, "ghe.corp", lambda _host: None)
