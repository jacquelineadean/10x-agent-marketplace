from datetime import date, timedelta

from speedup.core.analysis import (
    analyze_benchmark,
    analyze_change,
    analyze_journey,
    headline,
    priorities,
)
from speedup.core.model import BenchRun, Change
from speedup_helpers import project, steps

START = date(2026, 8, 1)


def test_lower_is_better_journey_reports_speedup_and_target() -> None:
    p = project()
    points = steps(START, 60, [(0, 1200.0), (20, 500.0)], wobble=0.02)
    result = analyze_journey(p.journey("load"), points, p)
    assert result["baseline"] == 1200.0
    assert result["current"] == 500.0
    assert result["speedup"] == 2.4
    assert result["improvement_pct"] == 58.3
    assert result["at_target"] is True and result["gap_to_target_pct"] == 0
    assert result["vs_baseline_p"] < 0.01
    assert result["status"] == "at-target"
    assert result["coverage_pct"] == 100.0


def test_higher_is_better_journey_counts_a_rise_as_a_win() -> None:
    p = project()
    points = steps(START, 40, [(0, 200.0), (15, 300.0)], wobble=0.01)
    result = analyze_journey(p.journey("throughput"), points, p)
    assert result["speedup"] == 1.5
    assert result["improvement_pct"] == 50.0
    assert result["gap_to_target_pct"] == 33.3
    assert result["status"] == "improving"


def test_a_significant_slowdown_against_the_previous_window_is_a_regression() -> None:
    p = project()
    points = steps(START, 40, [(0, 1000.0), (10, 500.0), (33, 600.0)], wobble=0.01)
    result = analyze_journey(p.journey("load"), points, p)
    assert result["vs_previous_pct"] == -20.0
    assert result["regressed"] is True
    assert result["status"] == "regressed"


def test_a_journey_without_data_says_so() -> None:
    p = project()
    assert analyze_journey(p.journey("load"), [], p)["status"] == "no-data"


def test_change_impact_compares_the_days_around_the_ship_day() -> None:
    p = project()
    history = {"load": steps(START, 40, [(0, 1000.0), (16, 600.0)], wobble=0.01)}
    shipped = START + timedelta(days=15)
    changes = [
        Change("c-0001", "Static composer", ["load"], shipped=shipped, stage="100%"),
        Change("c-0002", "Lazy menus", ["load"], shipped=shipped + timedelta(days=3)),
        Change("c-0003", "Not yet", ["load"]),
    ]
    journeys = {j.id: j for j in p.journeys}
    first = analyze_change(changes[0], changes, journeys, history, p)
    (row,) = first["impact"]
    assert row["verdict"] == "improved"
    assert row["before"] == 1000.0 and row["after"] == 600.0
    assert row["improvement_pct"] == 40.0
    assert first["overlaps"] == ["c-0002"]
    unshipped = analyze_change(changes[2], changes, journeys, history, p)
    assert unshipped["impact"][0]["verdict"] == "not shipped"


def test_change_impact_waits_for_enough_days_after_shipping() -> None:
    p = project()
    history = {"load": steps(START, 20, [(0, 1000.0)])}
    change = Change("c-0001", "Late", ["load"], shipped=START + timedelta(days=18))
    result = analyze_change(change, [change], {j.id: j for j in p.journeys}, history, p)
    assert result["impact"][0]["verdict"] == "too early"


def test_change_proxy_reduction_uses_the_benchmark_unit() -> None:
    p = project()
    change = Change("c-0001", "x", [], benchmark="tree", proxy_before=2000, proxy_after=1000)
    result = analyze_change(change, [change], {}, {}, p)
    assert result["proxy"] == {
        "benchmark": "tree",
        "unit": "instructions",
        "before": 2000,
        "after": 1000,
        "reduction_pct": 50.0,
    }


def test_benchmark_summary_tracks_ceiling_cut_and_latest_run() -> None:
    bench = project().benchmark("tree")
    runs = [
        BenchRun("tree", START, (1500.0,), 1500.0, 0.1),
        BenchRun("tree", START + timedelta(days=1), (990.0,), 990.0, 3.0),
        BenchRun("other", START, (1.0,), 1.0, 0.0),
    ]
    result = analyze_benchmark(bench, runs)
    assert result["ceiling_reduction_pct"] == 50.0
    assert result["latest"] == 990.0
    assert result["latest_reduction_pct"] == 50.5
    assert result["within_ceiling"] is True
    assert result["noisy"] is True
    assert result["runs"] == 2


def test_headline_uses_the_geometric_mean_and_counts_flags() -> None:
    journeys = {
        "a": {"speedup": 4.0, "target": 1, "at_target": True, "regressed": False},
        "b": {"speedup": 1.0, "target": 1, "at_target": False, "regressed": True},
        "c": {"target": None},
    }
    changes = [
        {
            "shipped": "2026-08-01",
            "flag": "f",
            "flag_removed": True,
            "stage": "100%",
            "impact": [{"verdict": "improved"}],
        },
        {"shipped": None, "flag": "g", "flag_removed": False, "stage": "employees", "impact": []},
    ]
    h = headline(journeys, changes, {"t": {"ceiling": 5, "ceiling_reduction_pct": 40.0}})
    assert h["geomean_speedup"] == 2.0
    assert h["best_journey"] == "a"
    assert (h["journeys_at_target"], h["journeys_with_target"], h["journeys_regressed"]) == (
        1,
        2,
        1,
    )
    assert (h["flags_added"], h["flags_removed"], h["flags_open"]) == (2, 1, 1)
    assert h["changes_improved"] == 1
    assert h["median_ceiling_reduction_pct"] == 40.0


def test_priorities_put_regressions_first_then_the_largest_weighted_gap() -> None:
    rows = priorities(
        {
            "a": {"gap_to_target_pct": 10.0, "weight": 5, "status": "improving"},
            "b": {"gap_to_target_pct": 80.0, "weight": 1, "status": "slower"},
            "c": {"gap_to_target_pct": 5.0, "weight": 1, "status": "regressed"},
            "d": {"gap_to_target_pct": 0.0, "weight": 9, "status": "at-target"},
        }
    )
    assert [r["journey"] for r in rows] == ["c", "b", "a"]
