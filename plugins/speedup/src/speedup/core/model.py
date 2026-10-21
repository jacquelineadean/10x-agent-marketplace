"""Domain records: the project file (journeys, benchmarks), daily points, changes, bench runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal

Direction = Literal["lower", "higher"]
SOURCE_KINDS = ("datadog-metric", "datadog-rum", "prometheus", "file")
PARSE_MODES = ("number", "valgrind", "json", "regex")
ROLLOUT_STAGES = ("dev", "employees", "1%", "5%", "10%", "25%", "50%", "100%", "rolled-back")


@dataclass(frozen=True)
class SourceQuery:
    """Where one journey's daily values come from. `scale` converts the source unit to `unit`."""

    kind: str
    query: str = ""
    measure: str = ""
    aggregation: str = "pc75"
    scale: float = 1.0


@dataclass(frozen=True)
class Journey:
    """One user interaction to make faster, measured at one percentile per day."""

    id: str
    name: str
    unit: str
    direction: Direction
    target: float | None
    weight: float
    source: SourceQuery


@dataclass(frozen=True)
class Benchmark:
    """A deterministic proxy for a journey: a command whose number can only go down."""

    id: str
    name: str
    command: tuple[str, ...]
    parse: str
    pattern: str
    unit: str
    repeat: int
    journeys: tuple[str, ...]
    ceiling: float | None
    original: float | None
    tolerance_pct: float
    headroom_pct: float
    max_cv_pct: float
    timeout_s: int


@dataclass(frozen=True)
class Window:
    since: date
    until: date

    @property
    def days(self) -> int:
        return (self.until - self.since).days + 1

    def contains(self, day: date) -> bool:
        return self.since <= day <= self.until


@dataclass(frozen=True)
class Project:
    """The parsed `perf/speedup.json`."""

    name: str
    percentile: str
    window_days: int
    regression_threshold_pct: float
    impact_days: int
    baseline: Window | None
    datadog_site: str
    prometheus_url: str
    journeys: tuple[Journey, ...]
    benchmarks: tuple[Benchmark, ...]

    def journey(self, journey_id: str) -> Journey:
        for journey in self.journeys:
            if journey.id == journey_id:
                return journey
        raise ValueError(f"unknown journey '{journey_id}'")

    def benchmark(self, benchmark_id: str) -> Benchmark:
        for benchmark in self.benchmarks:
            if benchmark.id == benchmark_id:
                return benchmark
        raise ValueError(f"unknown benchmark '{benchmark_id}'")


@dataclass(frozen=True)
class Point:
    day: date
    value: float


@dataclass(frozen=True)
class Series:
    """Daily values for one journey from one fetch or import, with where they came from."""

    journey: str
    points: tuple[Point, ...]
    source: str
    warnings: tuple[str, ...] = ()


@dataclass
class Change:
    """One optimization: what shipped, where, behind which flag, and its proxy numbers."""

    id: str
    title: str
    journeys: list[str]
    shipped: date | None = None
    pr: str = ""
    flag: str = ""
    stage: str = "dev"
    flag_removed: bool = False
    benchmark: str = ""
    proxy_before: float | None = None
    proxy_after: float | None = None
    notes: str = ""
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BenchRun:
    """One benchmark measured `len(values)` times on one day; the median is the result."""

    benchmark: str
    day: date
    values: tuple[float, ...]
    median: float
    cv_pct: float
    commit: str = ""
