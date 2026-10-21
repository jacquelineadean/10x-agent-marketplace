"""Run benchmark commands and read their number. Argument lists only: never a shell."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from datetime import date
from pathlib import Path

from perf_ratchet.core.model import Benchmark, BenchRun
from perf_ratchet.core.stats import cv_pct, median

_NUMBER = re.compile(r"-?\d[\d,]*(?:\.\d+)?(?:[eE][+-]?\d+)?")
_VALGRIND = re.compile(r"(?:I\s+refs|Collected)\s*:\s*([\d,]+)")

Executor = Callable[[list[str], int, Path], tuple[int, str, str]]


def execute(command: list[str], timeout: int, cwd: Path) -> tuple[int, str, str]:
    """Run one command; returns (exit code, stdout, stderr)."""
    try:
        done = subprocess.run(  # noqa: S603  argument list from the user's own project file, no shell
            command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False
        )
    except FileNotFoundError:
        raise ValueError(f"command not found: {command[0]}") from None
    except subprocess.TimeoutExpired:
        raise ValueError(f"'{' '.join(command)}' ran longer than {timeout}s") from None
    return done.returncode, done.stdout, done.stderr


def parse_output(benchmark: Benchmark, stdout: str, stderr: str) -> float:
    """number: last number on stdout; valgrind: `I refs` or `Collected`; json: dotted key; regex."""
    if benchmark.parse == "valgrind":
        matches = _VALGRIND.findall(stderr + "\n" + stdout)
        if not matches:
            raise ValueError(
                f"{benchmark.id}: no valgrind 'I refs' or 'Collected' line in the output"
            )
        return float(matches[-1].replace(",", ""))
    if benchmark.parse == "json":
        try:
            node = json.loads(stdout)
        except json.JSONDecodeError:
            raise ValueError(f"{benchmark.id}: stdout is not JSON") from None
        for part in benchmark.pattern.split("."):
            if not isinstance(node, dict) or part not in node:
                raise ValueError(f"{benchmark.id}: key {benchmark.pattern} not in the JSON output")
            node = node[part]
        return float(node)
    if benchmark.parse == "regex":
        found = re.findall(benchmark.pattern, stdout + "\n" + stderr)
        if not found:
            raise ValueError(f"{benchmark.id}: pattern matched nothing")
        last = found[-1]
        return float((last[0] if isinstance(last, tuple) else last).replace(",", ""))
    numbers = _NUMBER.findall(stdout)
    if not numbers:
        raise ValueError(f"{benchmark.id}: stdout has no number")
    return float(numbers[-1].replace(",", ""))


def run_benchmark(
    benchmark: Benchmark,
    day: date,
    cwd: Path,
    commit: str = "",
    executor: Executor = execute,
    repeat: int | None = None,
) -> BenchRun:
    values = []
    for _ in range(repeat or benchmark.repeat):
        code, stdout, stderr = executor(list(benchmark.command), benchmark.timeout_s, cwd)
        if code != 0:
            tail = (stderr or stdout).strip().splitlines()[-1:] or ["no output"]
            raise ValueError(f"{benchmark.id}: command exited {code}: {tail[0][:200]}")
        values.append(parse_output(benchmark, stdout, stderr))
    return BenchRun(benchmark.id, day, tuple(values), median(values), cv_pct(values), commit)
