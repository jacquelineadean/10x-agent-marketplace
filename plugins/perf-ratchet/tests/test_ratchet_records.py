import json
from datetime import UTC, date, datetime

import pytest
from perf_ratchet.core.model import Change, Point, Series
from perf_ratchet.core.records import (
    change_from,
    change_to,
    daily,
    merge,
    next_change_id,
    parse_bench_import,
    parse_import,
    points_of,
)


def _epoch(text: str) -> float:
    return datetime.fromisoformat(text).replace(tzinfo=UTC).timestamp()


def test_daily_takes_the_median_per_utc_day_and_skips_gaps() -> None:
    points = daily(
        [
            (_epoch("2026-10-01T01:00"), 100.0),
            (_epoch("2026-10-01T13:00"), 300.0),
            (_epoch("2026-10-01T23:00"), 200.0),
            (_epoch("2026-10-02T02:00"), float("nan")),
            (_epoch("2026-10-03T02:00"), 2.0),
        ],
        scale=1000,
    )
    assert points == (Point(date(2026, 10, 1), 200_000.0), Point(date(2026, 10, 3), 2000.0))


def test_merge_replaces_days_and_keeps_others_sorted() -> None:
    history = {"load": {"2026-10-02": 5.0, "2026-10-01": 1.0}}
    written = merge(history, Series("load", (Point(date(2026, 10, 2), 9.0),), "x"))
    assert written == 1
    assert list(history["load"].items()) == [("2026-10-01", 1.0), ("2026-10-02", 9.0)]
    assert points_of(history, "load")[1] == Point(date(2026, 10, 2), 9.0)


def test_import_reads_json_series_lists_and_csv() -> None:
    text = json.dumps(
        [
            {
                "journey": "load",
                "source": "datadog mcp",
                "points": [{"date": "2026-10-02", "value": 3}],
            }
        ]
    )
    (series,) = parse_import(text, "a.json", None)
    assert series.journey == "load" and series.source == "datadog mcp"
    (scaled,) = parse_import(
        '{"journey": "a", "scale": 1e-6, "points": [{"date": "2026-10-02", "value": 812400000}]}',
        "a.json",
        None,
    )
    assert scaled.points[0].value == pytest.approx(812.4)
    csv_series = parse_import("date,value,journey\n2026-10-01,5,a\n2026-10-01,6,b\n", "x.csv", None)
    assert {s.journey for s in csv_series} == {"a", "b"}
    (single,) = parse_import("date,value\n2026-10-01,5\n", "x.csv", "load")
    assert single.points[0].value == 5


@pytest.mark.parametrize(
    ("text", "name", "message"),
    [
        ("{", "a.json", "not valid JSON"),
        ('{"points": []}', "a.json", "no journey"),
        ('{"journey": "a", "points": [{"date": "soon", "value": 1}]}', "a.json", "YYYY-MM-DD"),
        (
            '{"journey": "a", "points": [{"date": "2026-01-01", "value": "inf"}]}',
            "a.json",
            "finite",
        ),
        ("day,ms\n1,2\n", "a.csv", "header"),
    ],
)
def test_bad_imports_fail_with_the_file_name(text: str, name: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_import(text, name, None)


def test_bench_import_is_detected_only_for_run_records() -> None:
    runs = parse_bench_import(
        json.dumps([{"benchmark": "tree", "date": "2026-10-01", "median": 5.0}]), "b.json"
    )
    assert runs is not None and runs[0].values == (5.0,)
    assert parse_bench_import('[{"journey": "a"}]', "b.json") is None
    assert parse_bench_import("date,value", "b.csv") is None
    with pytest.raises(ValueError, match="malformed"):
        parse_bench_import('[{"benchmark": "x"}]', "b.json")


def test_change_round_trip_keeps_unknown_fields() -> None:
    raw = {
        "id": "c-0001",
        "title": "Static composer",
        "journeys": ["load"],
        "shipped": "2026-08-11",
        "stage": "100%",
        "team": "web",
    }
    change = change_from(raw)
    assert change.extra == {"team": "web"}
    assert change_to(change)["team"] == "web"
    assert change_to(change)["shipped"] == "2026-08-11"


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ({"id": "1", "title": "x"}, "c-0001"),
        ({"id": "c-0001", "title": ""}, "title"),
        ({"id": "c-0001", "title": "x", "stage": "2%"}, "stage"),
        ({"id": "c-0001", "title": "x", "pr": "javascript:alert(1)"}, "http"),
    ],
)
def test_bad_changes_are_refused(raw: dict[str, str], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        change_from(raw)


def test_next_change_id_counts_up() -> None:
    assert next_change_id([]) == "c-0001"
    assert next_change_id([Change("c-0009", "a", []), Change("c-0002", "b", [])]) == "c-0010"
