"""Every file read and write: the project file, change log, data folder and outputs."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from perf_ratchet.core.model import BenchRun, Change
from perf_ratchet.core.records import History, bench_run_from, bench_run_to, change_from, change_to

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"{path} does not exist") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"{path} is not valid JSON: {error}") from None


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def read_changes(path: Path) -> list[Change]:
    if not path.is_file():
        return []
    changes = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            changes.append(change_from(json.loads(line)))
        except (json.JSONDecodeError, ValueError, KeyError) as error:
            raise ValueError(f"{path} line {number}: {error}") from None
    return changes


def write_changes(path: Path, changes: list[Change]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(change_to(c), separators=(",", ":")) for c in changes]
    path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


class DataFolder:
    """`~/perf-ratchet-runs/<project>/`: history, benchmark runs, raw responses and outputs."""

    def __init__(self, root: Path) -> None:
        self.root = root

    @property
    def history_path(self) -> Path:
        return self.root / "history.json"

    @property
    def bench_path(self) -> Path:
        return self.root / "bench.json"

    def history(self) -> History:
        if not self.history_path.is_file():
            return {}
        data = read_json(self.history_path)
        return {str(k): {str(d): float(v) for d, v in days.items()} for k, days in data.items()}

    def save_history(self, history: History) -> None:
        write_json(self.history_path, history)

    def bench_runs(self) -> list[BenchRun]:
        if not self.bench_path.is_file():
            return []
        return [bench_run_from(item) for item in read_json(self.bench_path)]

    def add_bench_runs(self, runs: list[BenchRun]) -> None:
        kept = [
            r
            for r in self.bench_runs()
            if (r.benchmark, r.day) not in {(n.benchmark, n.day) for n in runs}
        ]
        write_json(self.bench_path, [bench_run_to(r) for r in [*kept, *runs]])

    def record_raw(self, name: str, body: Any) -> None:
        write_json(self.root / "raw" / f"{_SAFE_NAME.sub('_', name)}.json", body)

    def path(self, name: str) -> Path:
        return self.root / name
