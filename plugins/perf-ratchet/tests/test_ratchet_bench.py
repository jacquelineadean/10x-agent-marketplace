import sys
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from perf_ratchet.connectors.bench.runner import execute, parse_output, run_benchmark
from ratchet_helpers import FIXTURES, project

DAY = date(2026, 10, 1)


def _bench(**changes: object):  # type: ignore[no-untyped-def]
    return replace(project().benchmark("tree"), **changes)


def test_parse_modes_read_the_right_number() -> None:
    valgrind = (FIXTURES / "valgrind_cachegrind.txt").read_text()
    assert parse_output(_bench(parse="valgrind"), "", valgrind) == 590_123_456
    assert parse_output(_bench(parse="number"), "warmup 3\nresult: 1,234.5\n", "") == 1234.5
    assert parse_output(_bench(parse="json", pattern="a.b"), '{"a": {"b": 7}}', "") == 7
    assert parse_output(_bench(parse="regex", pattern=r"commits=(\d+)"), "commits=12", "") == 12


@pytest.mark.parametrize(
    ("changes", "stdout", "message"),
    [
        ({"parse": "valgrind"}, "", "valgrind"),
        ({"parse": "number"}, "no digits", "no number"),
        ({"parse": "json", "pattern": "a"}, "nope", "not JSON"),
        ({"parse": "json", "pattern": "a.c"}, '{"a": {"b": 1}}', "not in the JSON"),
        ({"parse": "regex", "pattern": r"x=(\d+)"}, "y=1", "matched nothing"),
    ],
)
def test_unreadable_output_says_why(changes: dict[str, str], stdout: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_output(_bench(**changes), stdout, "")


def test_run_takes_the_median_and_reports_noise() -> None:
    outputs = iter(["100", "104", "102"])
    calls: list[list[str]] = []

    def fake(command: list[str], timeout: int, cwd: Path) -> tuple[int, str, str]:
        calls.append(command)
        return 0, next(outputs), ""

    run = run_benchmark(_bench(repeat=3), DAY, Path(), "abc123", fake)
    assert run.values == (100.0, 104.0, 102.0)
    assert run.median == 102.0
    assert round(run.cv_pct, 2) == 1.96
    assert run.commit == "abc123"
    assert calls[0] == ["node", "bench.js"]


def test_a_failing_command_stops_with_its_last_line() -> None:
    def fake(command: list[str], timeout: int, cwd: Path) -> tuple[int, str, str]:
        return 2, "", "loading\nError: cannot find bench.js\n"

    with pytest.raises(ValueError, match="exited 2: Error: cannot find bench.js"):
        run_benchmark(_bench(), DAY, Path(), executor=fake)


def test_execute_runs_an_argument_list_without_a_shell(tmp_path: Path) -> None:
    code, stdout, _ = execute([sys.executable, "-c", "print(6 * 7)"], 30, tmp_path)
    assert (code, stdout.strip()) == (0, "42")
    with pytest.raises(ValueError, match="command not found"):
        execute(["perf-ratchet-no-such-command"], 30, tmp_path)
