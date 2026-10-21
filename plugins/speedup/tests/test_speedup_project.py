import json
from typing import Any

import pytest
from speedup.core.project import ProjectError, parse_project, with_ceilings
from speedup_helpers import DEMO, project


def _raw(**overrides: Any) -> dict[str, Any]:
    raw: dict[str, Any] = {
        "project": "x",
        "journeys": [{"id": "load", "source": {"kind": "datadog-metric", "query": "p75:a{*}"}}],
    }
    raw.update(overrides)
    return raw


def test_demo_project_parses_with_every_source_kind() -> None:
    parsed = parse_project(json.loads((DEMO / "perf" / "speedup.json").read_text()))
    kinds = {j.source.kind for j in parsed.journeys}
    assert kinds == {"datadog-rum", "datadog-metric", "prometheus"}
    assert len(parsed.journeys) == 9
    assert parsed.benchmark("message-tree").parse == "valgrind"
    assert parsed.baseline is not None and parsed.baseline.days == 7


def test_defaults_fill_percentile_windows_and_direction() -> None:
    parsed = parse_project(_raw())
    assert parsed.percentile == "p75"
    assert parsed.window_days == 7
    assert parsed.journeys[0].direction == "lower"
    assert parsed.journeys[0].unit == "ms"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"schema_version": 2}, "schema_version"),
        ({"percentile": "p42"}, "percentile"),
        ({"journeys": [{"id": "Bad Id"}]}, "lowercase"),
        ({"journeys": [{"id": "a", "source": {"kind": "newrelic"}}]}, "kind"),
        ({"journeys": [{"id": "a", "source": {"kind": "prometheus"}}]}, "query is required"),
        (
            {"journeys": [{"id": "a", "source": {"kind": "datadog-rum", "query": "@type:view"}}]},
            "RUM attribute",
        ),
        ({"journeys": [{"id": "a", "target": -1}]}, "target"),
        ({"journeys": [{"id": "a"}, {"id": "a"}]}, "appears twice"),
        ({"baseline": {"since": "2026-08-07", "until": "2026-08-01"}}, "before"),
        ({"window_days": 0}, "window_days"),
    ],
)
def test_bad_values_name_the_field(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ProjectError, match=message):
        parse_project(_raw(**overrides))


@pytest.mark.parametrize(
    ("benchmark", "message"),
    [
        ({"id": "b", "command": "node bench.js"}, "list of strings"),
        ({"id": "b", "command": ["node"], "parse": "regex"}, "pattern is required"),
        ({"id": "b", "command": ["node"], "parse": "regex", "pattern": r"\d+"}, "capture group"),
        ({"id": "b", "command": ["node"], "parse": "regex", "pattern": "("}, "not a valid regex"),
        ({"id": "b", "command": ["node"], "journeys": ["nope"]}, "unknown journeys"),
        ({"id": "b", "command": ["node"], "ceiling": 0}, "ceiling"),
    ],
)
def test_bad_benchmarks_are_refused(benchmark: dict[str, Any], message: str) -> None:
    with pytest.raises(ProjectError, match=message):
        parse_project(_raw(benchmarks=[benchmark]))


def test_with_ceilings_changes_only_named_benchmarks_and_keeps_unknown_keys() -> None:
    raw = _raw(
        benchmarks=[
            {"id": "a", "command": ["x"], "ceiling": 10, "note": "kept"},
            {"id": "b", "command": ["y"], "ceiling": 20},
        ]
    )
    updated = with_ceilings(raw, {"a": (8.0, 12.0)})
    assert updated["benchmarks"][0] == {
        "id": "a",
        "command": ["x"],
        "ceiling": 8.0,
        "original": 12.0,
        "note": "kept",
    }
    assert updated["benchmarks"][1]["ceiling"] == 20
    assert raw["benchmarks"][0]["ceiling"] == 10


def test_lookups_name_unknown_ids() -> None:
    with pytest.raises(ValueError, match="unknown journey 'x'"):
        project().journey("x")
    with pytest.raises(ValueError, match="unknown benchmark 'x'"):
        project().benchmark("x")
