"""Write the demo's invented field data and benchmark runs. Deterministic: seed 7.

Lumen is a made-up chat app. Its numbers echo the shape of a two-week speed sprint: a
baseline week, most wins in the sprint, a long tail of smaller changes, and one regression
that the daily measure catches in October.

Run from the repo root: `python3 plugins/perf-ratchet/examples/demo/generate.py`.
"""

from __future__ import annotations

import json
import math
import random
import sys
from datetime import date, timedelta
from pathlib import Path

HERE = Path(__file__).parent
START, END = date(2026, 7, 27), date(2026, 10, 18)
RNG = random.Random(7)  # noqa: S311  invented demo data, not security-relevant

# journey: baseline level, then (ship day, new level) steps; noise is the daily spread.
JOURNEYS: dict[str, tuple[float, list[tuple[str, float]], float]] = {
    "fresh-load": (
        3085,
        [
            ("2026-08-11", 1900),
            ("2026-08-14", 1240),
            ("2026-08-18", 820),
            ("2026-08-21", 600),
            ("2026-09-08", 550),
        ],
        0.05,
    ),
    "conversation-switch": (
        1240,
        [("2026-08-12", 860), ("2026-08-17", 520), ("2026-08-24", 410), ("2026-09-15", 380)],
        0.05,
    ),
    "new-chat": (960, [("2026-08-13", 640), ("2026-08-20", 420), ("2026-09-01", 310)], 0.05),
    "send-to-paint": (420, [("2026-08-12", 300), ("2026-08-19", 210), ("2026-09-22", 160)], 0.04),
    "sidebar-open": (310, [("2026-08-15", 140), ("2026-08-25", 95)], 0.06),
    "search-results": (880, [("2026-08-26", 640), ("2026-09-10", 520), ("2026-10-09", 615)], 0.05),
    "desktop-cold-start": (
        2600,
        [("2026-08-14", 1500), ("2026-08-22", 960), ("2026-09-18", 730)],
        0.05,
    ),
    "long-thread-scroll": (180, [("2026-08-18", 128), ("2026-08-27", 96)], 0.05),
    "history-api": (340, [("2026-08-20", 260), ("2026-09-29", 214)], 0.04),
}

# benchmark: first value, then (day, new value) steps, daily noise as a fraction.
BENCHMARKS: dict[str, tuple[float, list[tuple[str, float]], float]] = {
    "message-tree": (1.24e9, [("2026-08-12", 6.45e8), ("2026-08-24", 5.9e8)], 0.0015),
    "markdown-render": (8.6e8, [("2026-08-19", 5.93e8), ("2026-09-22", 5.1e8)], 0.0015),
    "sidebar-commits": (42, [("2026-08-15", 9), ("2026-08-25", 6)], 0.0),
    "main-boot": (
        2.1e9,
        [("2026-08-14", 1.32e9), ("2026-08-22", 9.8e8), ("2026-09-18", 8.4e8)],
        0.002,
    ),
    "composer-mutations": (1180, [("2026-08-11", 410), ("2026-08-18", 160)], 0.0),
    "search-index": (3.3e8, [("2026-08-26", 2.2e8), ("2026-09-10", 1.7e8)], 0.0015),
}


def level(base: float, steps: list[tuple[str, float]], day: date) -> float:
    value = base
    for shipped, new in steps:
        if day > date.fromisoformat(shipped):
            value = new
    return value


def journeys() -> list[dict[str, object]]:
    out = []
    for journey, (base, steps, spread) in JOURNEYS.items():
        points = []
        day = START
        while day <= END:
            weekend = 1.03 if day.weekday() >= 5 else 1.0
            value = level(base, steps, day) * weekend * math.exp(RNG.gauss(0, spread))
            points.append({"date": day.isoformat(), "value": round(value, 1)})
            day += timedelta(days=1)
        out.append({"journey": journey, "source": "demo data (invented)", "points": points})
    return out


def bench_runs() -> list[dict[str, object]]:
    out = []
    for bench, (base, steps, spread) in BENCHMARKS.items():
        day = date(2026, 8, 10)
        while day <= END:
            center = level(base, steps, day + timedelta(days=1))
            values = [round(center * (1 + RNG.gauss(0, spread)), 0) for _ in range(3)]
            ordered = sorted(values)
            mean = sum(values) / 3
            spread_pct = 0.0
            if mean and len(set(values)) > 1:
                spread_pct = (sum((v - mean) ** 2 for v in values) / 2) ** 0.5 / mean * 100
            out.append(
                {
                    "benchmark": bench,
                    "date": day.isoformat(),
                    "values": values,
                    "median": ordered[1],
                    "cv_pct": round(spread_pct, 3),
                    "commit": "",
                }
            )
            day += timedelta(days=1)
    return out


def main() -> int:
    imports = HERE / "imports"
    imports.mkdir(exist_ok=True)
    (imports / "journeys.json").write_text(
        json.dumps(journeys(), indent=1) + "\n", encoding="utf-8"
    )
    (imports / "bench-runs.json").write_text(
        json.dumps(bench_runs(), indent=1) + "\n", encoding="utf-8"
    )
    sys.stdout.write(f"wrote {imports}/journeys.json and bench-runs.json\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
