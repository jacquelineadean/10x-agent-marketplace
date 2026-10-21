"""The ratchet: a benchmark's ceiling only moves down, and CI fails a change that crosses it.

`guard` compares fresh benchmark numbers with ceilings. `tighten` lowers each ceiling to the
latest number plus a little headroom, and never raises one.
"""

from __future__ import annotations

from dataclasses import dataclass

from perf_ratchet.core.model import Benchmark, BenchRun


@dataclass(frozen=True)
class Verdict:
    benchmark: str
    value: float
    ceiling: float | None
    limit: float | None
    cv_pct: float
    outcome: str  # pass, fail, noisy, new

    def line(self) -> str:
        if self.ceiling is None:
            return f"{self.benchmark}: {self.value:,.0f} (no ceiling yet; tighten sets one)"
        delta = (self.value / self.ceiling - 1) * 100
        return (
            f"{self.benchmark}: {self.value:,.0f} vs ceiling {self.ceiling:,.0f} "
            f"({delta:+.2f}%, cv {self.cv_pct:.2f}%) {self.outcome.upper()}"
        )


def judge(benchmark: Benchmark, run: BenchRun) -> Verdict:
    """Fail above ceiling plus tolerance; a run noisier than `max_cv_pct` is marked noisy."""
    if benchmark.ceiling is None:
        return Verdict(benchmark.id, run.median, None, None, run.cv_pct, "new")
    limit = benchmark.ceiling * (1 + benchmark.tolerance_pct / 100)
    if run.median > limit:
        outcome = "fail"
    elif run.cv_pct > benchmark.max_cv_pct:
        outcome = "noisy"
    else:
        outcome = "pass"
    return Verdict(benchmark.id, run.median, benchmark.ceiling, limit, run.cv_pct, outcome)


@dataclass(frozen=True)
class Tightening:
    benchmark: str
    old: float | None
    new: float
    original: float

    @property
    def moved(self) -> bool:
        return self.old is None or self.new < self.old

    def line(self) -> str:
        if self.old is None:
            return f"{self.benchmark}: ceiling set to {self.new:,.0f}"
        if not self.moved:
            return f"{self.benchmark}: ceiling stays {self.old:,.0f}"
        cut = (1 - self.new / self.old) * 100
        return f"{self.benchmark}: ceiling {self.old:,.0f} -> {self.new:,.0f} (-{cut:.2f}%)"


def tighten(benchmark: Benchmark, run: BenchRun) -> Tightening | None:
    """New ceiling = latest median plus headroom, kept only if lower. Noisy runs never move it."""
    if run.cv_pct > benchmark.max_cv_pct:
        return None
    candidate = run.median * (1 + benchmark.headroom_pct / 100)
    original = benchmark.original or benchmark.ceiling or run.median
    if benchmark.ceiling is not None and candidate >= benchmark.ceiling:
        return Tightening(benchmark.id, benchmark.ceiling, benchmark.ceiling, original)
    return Tightening(benchmark.id, benchmark.ceiling, round(candidate, 3), original)
