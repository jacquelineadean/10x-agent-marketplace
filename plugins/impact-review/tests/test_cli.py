import io
import json
from pathlib import Path

import pytest
from conftest import TODAY, TOKEN, FakeGitHub, Reply, fixture, recorded_github, transport_for
from impact_review.connectors.github.source import GitHubSource
from impact_review.core.ports import ActivitySource
from impact_review.entrypoints.cli.main import run


def _factory(github: FakeGitHub):  # type: ignore[no-untyped-def]
    def make_source(host: str) -> ActivitySource:
        return GitHubSource(transport_for(github, host))

    return make_source


def _run(
    github: FakeGitHub, argv: list[str], env: dict[str, str] | None = None
) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    code = run(argv, _factory(github), env or {}, today=TODAY, out=out, err=err)
    return code, out.getvalue(), err.getvalue()


def test_collect_writes_the_run_folder_and_prints_at_most_15_lines(tmp_path: Path) -> None:
    github = recorded_github()
    code, out, err = _run(
        github,
        [
            "collect",
            "--timeframe",
            "2026-01-01..2026-09-30",
            "--out",
            str(tmp_path),
            "--repo-share",
        ],
    )
    assert code == 0, err
    lines = out.strip().splitlines()
    assert 1 <= len(lines) <= 15
    assert lines[0] == f"run folder: {tmp_path}"
    assert "commits 7, PRs opened 4, merged 2, reviews 3, issues 1, repos 3" in out
    assert "within cap" in out
    assert TOKEN not in out + err
    names = {p.name for p in tmp_path.iterdir()}
    assert names == {
        "raw",
        "metrics.json",
        "digest.md",
        "dashboard.md",
        "dashboard.html",
        "budget.json",
        "rubric.md",
    }
    metrics = json.loads((tmp_path / "metrics.json").read_text())
    assert metrics["schema_version"] == 2
    assert metrics["volume"]["prs_merged"] == 2
    assert "## Delivery and impact" in (tmp_path / "rubric.md").read_text()
    budget = json.loads((tmp_path / "budget.json").read_text())
    assert budget["within_cap"] is True
    assert budget["parts"]["rubric_and_writer_instructions"] > 0
    assert "digest" not in out.lower() or "digest.md" in out


def test_default_run_folder_is_host_login_timeframe(tmp_path: Path) -> None:
    code, out, _ = _run(
        recorded_github(),
        ["collect", "--timeframe", "last 30d"],
        {"IMPACT_REVIEW_RUNS": str(tmp_path)},
    )
    assert code == 0
    assert (tmp_path / "github.com" / "srivera" / "2026-09-12_2026-10-11" / "digest.md").is_file()
    assert "run folder: " + str(tmp_path / "github.com" / "srivera") in out


def test_since_and_until_override_timeframe(tmp_path: Path) -> None:
    code, out, _ = _run(
        recorded_github(),
        ["collect", "--since", "2026-01-01", "--until", "2026-09-30", "--out", str(tmp_path)],
    )
    assert code == 0
    assert "timeframe: 2026-01-01 to 2026-09-30 (2026-01-01..2026-09-30, 273 days)" in out


def test_over_cap_exits_2_and_says_what_to_do(tmp_path: Path) -> None:
    code, out, _ = _run(
        recorded_github(),
        [
            "collect",
            "--out",
            str(tmp_path),
            "--max-tokens",
            "10000",
            "--timeframe",
            "2026-01-01..2026-09-30",
        ],
    )
    assert code == 2
    assert "OVER CAP" in out
    assert "raise --max-tokens" in out
    assert (tmp_path / "digest.md").is_file()


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["collect", "--timeframe", "yesterday"], "unknown timeframe"),
        (["collect", "--since", "2026-01-01"], "--since and --until go together"),
    ],
)
def test_bad_input_exits_1_with_a_message(argv: list[str], message: str) -> None:
    code, out, err = _run(recorded_github(), argv)
    assert code == 1
    assert out == ""
    assert message in err


def test_sso_error_prints_the_authorization_step(tmp_path: Path) -> None:
    github = FakeGitHub().on("Viewer", Reply(body=fixture("sso_error")))
    code, _, err = _run(github, ["collect", "--out", str(tmp_path)])
    assert code == 1
    assert "organization acme requires SSO authorization" in err


def test_second_run_uses_the_cache(tmp_path: Path) -> None:
    github = recorded_github()
    argv = ["collect", "--timeframe", "2026-01-01..2026-09-30", "--out", str(tmp_path)]
    assert _run(github, argv)[0] == 0
    calls = len(github.sent)
    assert _run(github, argv)[0] == 0
    assert len(github.sent) == calls + 1
    assert _run(github, [*argv, "--refresh"])[0] == 0
    assert len(github.sent) == 2 * calls + 1


def test_main_wires_settings_token_and_transport(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import impact_review.__main__ as entry
    from impact_review.connectors.github.http import GitHubTransport

    github = recorded_github()
    seen: list[str] = []

    def transport(endpoints, token):  # type: ignore[no-untyped-def]
        seen.append(token)
        return GitHubTransport(endpoints, token, opener=github, sleeper=github.sleep)

    monkeypatch.setattr(entry, "GitHubTransport", transport)
    monkeypatch.setattr(
        entry,
        "load_environment",
        lambda: {"GITHUB_TOKEN": "env-token", "IMPACT_REVIEW_RUNS": str(tmp_path)},
    )
    monkeypatch.setattr("sys.stdout", io.StringIO())
    assert entry.main(["collect", "--timeframe", "2026-01-01..2026-09-30"]) == 0
    assert (
        tmp_path / "github.com" / "srivera" / "2026-01-01_2026-09-30" / "metrics.json"
    ).is_file()
    assert github.sent[0].headers["Authorization"] == "Bearer env-token"
    assert seen == ["env-token"]
