from dataclasses import replace
from datetime import date

from speedup.core.model import BenchRun
from speedup.core.ratchet import judge, tighten
from speedup_helpers import project

DAY = date(2026, 10, 1)


def _run(value: float, cv: float = 0.1) -> BenchRun:
    return BenchRun("tree", DAY, (value,), value, cv)


def test_guard_passes_within_tolerance_and_fails_above_it() -> None:
    bench = project().benchmark("tree")
    assert judge(bench, _run(1009)).outcome == "pass"
    failed = judge(bench, _run(1011))
    assert failed.outcome == "fail"
    assert "FAIL" in failed.line() and "+1.10%" in failed.line()


def test_noisy_runs_are_marked_and_new_benchmarks_have_no_ceiling() -> None:
    bench = project().benchmark("tree")
    assert judge(bench, _run(900, cv=5)).outcome == "noisy"
    fresh = replace(bench, ceiling=None)
    assert judge(fresh, _run(900)).outcome == "new"


def test_tighten_lowers_with_headroom_and_never_raises() -> None:
    bench = project().benchmark("tree")
    lowered = tighten(bench, _run(800))
    assert lowered is not None and lowered.moved
    assert lowered.new == 804.0 and lowered.original == 2000
    kept = tighten(bench, _run(1200))
    assert kept is not None and not kept.moved and kept.new == 1000
    assert "stays" in kept.line()


def test_tighten_ignores_noisy_runs_and_sets_a_first_ceiling() -> None:
    bench = project().benchmark("tree")
    assert tighten(bench, _run(500, cv=9)) is None
    first = tighten(replace(bench, ceiling=None, original=None), _run(500))
    assert first is not None and first.old is None and first.original == 500 and first.new == 502.5
