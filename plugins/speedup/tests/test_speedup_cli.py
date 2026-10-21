import io
import json
import shutil
from datetime import date
from pathlib import Path

import pytest
from speedup.__main__ import main
from speedup.core.model import Journey, Point, Project, Series, Window
from speedup.entrypoints.cli.main import EXIT_ERROR, EXIT_FLAGGED, EXIT_OK, run
from speedup_helpers import DEMO

TODAY = date(2026, 10, 19)


class FakeSource:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Window]] = []

    def fetch(self, journey: Journey, window: Window) -> Series:
        self.calls.append((journey.id, window))
        return Series(journey.id, (Point(window.until, 123.0),), "fake", ("note",))


def _cli(args: list[str], config: Path, data: Path, **kwargs: object) -> tuple[int, str, str]:
    out, err = io.StringIO(), io.StringIO()
    source = kwargs.pop("source", FakeSource())

    def make(kind: str, project: Project, folder: object) -> FakeSource:
        return source  # type: ignore[return-value]

    code = run(
        ["--config", str(config), "--data", str(data), *args],
        make,  # type: ignore[arg-type]
        {},
        today=TODAY,
        out=out,
        err=err,
        **kwargs,  # type: ignore[arg-type]
    )
    return code, out.getvalue(), err.getvalue()


@pytest.fixture
def demo(tmp_path: Path) -> Path:
    shutil.copytree(DEMO / "perf", tmp_path / "perf")
    return tmp_path


def test_init_writes_a_starter_that_parses_and_refuses_to_overwrite(tmp_path: Path) -> None:
    config = tmp_path / "perf" / "speedup.json"
    code, out, _ = _cli(["init", "--project", "shop"], config, tmp_path / "data")
    assert code == EXIT_OK and "wrote" in out
    assert json.loads(config.read_text())["project"] == "shop"
    assert (tmp_path / "perf" / "changes.jsonl").exists()
    code, _, err = _cli(["init"], config, tmp_path / "data")
    assert code == EXIT_ERROR and "--force" in err


def test_demo_import_and_report_write_every_output(demo: Path) -> None:
    data = demo / "data"
    config = demo / "perf" / "speedup.json"
    files = [str(p) for p in sorted((DEMO / "imports").glob("*.json"))]
    code, out, _ = _cli(["import", *files], config, data)
    assert code == EXIT_OK and "420 benchmark runs" in out
    code, out, _ = _cli(["report"], config, data)
    assert code == EXIT_OK
    lines = out.splitlines()
    assert len(lines) <= 15
    assert "REGRESSION search-results" in out
    assert "within cap" in out
    for name in ("metrics.json", "digest.md", "dashboard.html", "artifact.html", "budget.json"):
        assert (data / name).is_file()
    metrics = json.loads((data / "metrics.json").read_text())
    assert metrics["headline"]["journeys_at_target"] == 6
    assert metrics["journeys"]["search-results"]["status"] == "regressed"
    assert metrics["headline"]["guardrails_with_ceiling"] == 6


def test_report_exits_2_over_the_token_cap(demo: Path) -> None:
    code, out, _ = _cli(
        ["report", "--max-tokens", "1000"], demo / "perf" / "speedup.json", demo / "d"
    )
    assert code == EXIT_FLAGGED and "OVER CAP" in out


def test_measure_fetches_each_non_file_journey_for_the_window(demo: Path) -> None:
    source = FakeSource()
    code, out, _ = _cli(
        ["measure", "--days", "14", "--journey", "fresh-load"],
        demo / "perf" / "speedup.json",
        demo / "data",
        source=source,
    )
    assert code == EXIT_OK
    assert source.calls == [("fresh-load", Window(date(2026, 10, 5), date(2026, 10, 18)))]
    history = json.loads((demo / "data" / "history.json").read_text())
    assert history == {"fresh-load": {"2026-10-18": 123.0}}
    assert "warning: note" in out


def test_measure_rejects_half_a_date_range(demo: Path) -> None:
    code, _, err = _cli(
        ["measure", "--since", "2026-10-01"], demo / "perf" / "speedup.json", demo / "d"
    )
    assert code == EXIT_ERROR and "go together" in err


def test_log_adds_then_updates_a_change(demo: Path) -> None:
    config = demo / "perf" / "speedup.json"
    code, out, _ = _cli(
        [
            "log",
            "--title",
            "Defer analytics",
            "--journey",
            "fresh-load",
            "--flag",
            "defer_analytics",
            "--stage",
            "employees",
            "--benchmark",
            "composer-mutations",
            "--before",
            "160",
            "--after",
            "120",
        ],
        config,
        demo / "d",
    )
    assert code == EXIT_OK and "added c-0021" in out
    code, out, _ = _cli(
        ["log", "--id", "c-0021", "--stage", "100%", "--flag-removed"], config, demo / "d"
    )
    assert code == EXIT_OK and "updated c-0021" in out
    last = json.loads((demo / "perf" / "changes.jsonl").read_text().splitlines()[-1])
    assert last["stage"] == "100%" and last["flag_removed"] is True
    assert last["shipped"] == "2026-10-19"
    assert last["proxy_after"] == 120.0


def test_log_refuses_unknown_journeys_and_ids(demo: Path) -> None:
    config = demo / "perf" / "speedup.json"
    code, _, err = _cli(["log", "--title", "x", "--journey", "nope"], config, demo / "d")
    assert code == EXIT_ERROR and "unknown journey" in err
    code, _, err = _cli(["log", "--id", "c-9999", "--stage", "1%"], config, demo / "d")
    assert code == EXIT_ERROR and "no change c-9999" in err


def test_guard_fails_over_the_ceiling_and_passes_under_it(demo: Path) -> None:
    config = demo / "perf" / "speedup.json"
    values = demo / "values.json"
    values.write_text(json.dumps({"message-tree": 700_000_000}))
    code, out, _ = _cli(
        ["guard", "--benchmark", "message-tree", "--values", str(values)], config, demo / "d"
    )
    assert code == EXIT_FLAGGED and "FAILED" in out
    values.write_text(json.dumps({"message-tree": 580_000_000}))
    code, out, _ = _cli(
        ["guard", "--benchmark", "message-tree", "--values", str(values)], config, demo / "d"
    )
    assert code == EXIT_OK and "passed" in out


def test_tighten_writes_lower_ceilings_only(demo: Path) -> None:
    config = demo / "perf" / "speedup.json"
    values = demo / "values.json"
    values.write_text(json.dumps({"message-tree": 500_000_000, "markdown-render": 900_000_000}))
    args = [
        "tighten",
        "--benchmark",
        "message-tree",
        "--benchmark",
        "markdown-render",
        "--values",
        str(values),
    ]
    code, out, _ = _cli([*args, "--dry-run"], config, demo / "d")
    assert code == EXIT_OK and "dry run: 1 ceilings would move" in out
    code, out, _ = _cli(args, config, demo / "d")
    benchmarks = {b["id"]: b for b in json.loads(config.read_text())["benchmarks"]}
    assert benchmarks["message-tree"]["ceiling"] == 502_500_000
    assert benchmarks["message-tree"]["original"] == 1_240_000_000
    assert benchmarks["markdown-render"]["ceiling"] == 512_550_000
    assert "wrote 1 ceilings" in out


def test_bench_runs_commands_and_records_results(demo: Path) -> None:
    def executor(command: list[str], timeout: int, cwd: Path) -> tuple[int, str, str]:
        return 0, '{"commits": 6}', ""

    code, out, _ = _cli(
        ["bench", "--benchmark", "sidebar-commits"],
        demo / "perf" / "speedup.json",
        demo / "d",
        executor=executor,
    )
    assert code == EXIT_OK and "sidebar-commits: 6 vs ceiling 6" in out
    runs = json.loads((demo / "d" / "bench.json").read_text())
    assert runs == [
        {
            "benchmark": "sidebar-commits",
            "date": "2026-10-19",
            "values": [6.0],
            "median": 6.0,
            "cv_pct": 0.0,
            "commit": "",
        }
    ]


def test_writeup_fills_tokens_and_flags_hand_typed_numbers(demo: Path) -> None:
    config, data = demo / "perf" / "speedup.json", demo / "data"
    _cli(["import", *[str(p) for p in (DEMO / "imports").glob("*.json")]], config, data)
    _cli(["report"], config, data)
    (data / "writeup.src.md").write_text(
        "# How Lumen got {{headline.geomean_speedup}} faster\n\nFresh load: "
        "{{journeys.fresh-load.baseline}} to {{journeys.fresh-load.current}}.\n"
    )
    code, out, _ = _cli(["writeup"], config, data)
    assert code == EXIT_OK, out
    text = (data / "writeup.md").read_text()
    assert text.startswith("# How Lumen got 2.68x faster")
    assert "## Numbers and their sources" in text
    assert 'id="writeup"' in (data / "artifact.html").read_text()
    (data / "writeup.src.md").write_text("We shipped 20 changes. {{journeys.nope.x}}\n")
    code, out, _ = _cli(["writeup"], config, data)
    assert code == EXIT_FLAGGED
    assert "unknown keys: journeys.nope.x" in out and "numbers typed by hand: 20" in out


def test_main_names_missing_datadog_keys(
    demo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.chdir(demo)
    for name in ("DD_API_KEY", "DD_APP_KEY", "DD_APPLICATION_KEY"):
        monkeypatch.delenv(name, raising=False)
    code = main(["--data", str(demo / "d"), "measure", "--journey", "fresh-load"])
    assert code == EXIT_ERROR
    assert "DD_API_KEY and DD_APP_KEY" in capsys.readouterr().err
