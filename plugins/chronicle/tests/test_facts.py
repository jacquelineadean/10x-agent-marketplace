from __future__ import annotations

import pytest
from chronicle.core.story.facts import (
    FactError,
    format_value,
    lookup,
    resolve_refs,
    unsourced_numbers,
)

FACTS = {
    "delivery": {
        "deploys": {"value": 37, "unit": "per week", "source": "github", "note": "Sep 2026"},
        "weekly": [1, 2, 3],
    },
    "cost": {"saving": {"value": 335000, "unit": "$", "source": "finance"}},
    "slo": {"value": 99.95, "unit": "%"},
}


def test_lookup_reads_value_records_with_source_and_note() -> None:
    fact = lookup(FACTS, "delivery.deploys")
    assert (fact.value, fact.unit, fact.source, fact.note) == (37, "per week", "github", "Sep 2026")


def test_lookup_reads_list_items_by_index() -> None:
    assert lookup(FACTS, "delivery.weekly.2").value == 3


def test_lookup_names_the_keys_that_do_exist() -> None:
    with pytest.raises(FactError, match="deploys, weekly"):
        lookup(FACTS, "delivery.deploy")


@pytest.mark.parametrize(
    ("value", "unit", "fmt", "expected"),
    [
        (1284, "", "auto", "1,284"),
        (99.95, "%", "auto", "99.95%"),
        (71, "%", "auto", "71%"),
        (1.6, "days", "auto", "1.6 days"),
        (1, "days", "auto", "1 day"),
        (420, "ms", "auto", "420 ms"),
        (335000, "$", "auto", "$335K"),
        (1.9e6, "$", "auto", "$1.9M"),
        (12, "pts", "signed", "+12 pts"),
        (-3, "", "auto", "−3"),
        (37, "per week", "plain", "37"),
        (400000, "", "compact", "400K"),
        ("2026-11-03", "", "date", "3 Nov 2026"),
        ("2027-06", "", "month", "Jun 2027"),
    ],
)
def test_format_value(value: object, unit: str, fmt: str, expected: str) -> None:
    assert format_value(value, unit, fmt) == expected


def test_format_value_rejects_impossible_dates() -> None:
    with pytest.raises(FactError, match="not a real date"):
        format_value("2026-02-30", fmt="date")


def test_resolve_refs_swaps_at_paths_for_raw_values() -> None:
    spec = {"data": {"values": "@delivery.weekly", "now": "@delivery.deploys"}, "title": "@ x"}
    assert resolve_refs(spec, FACTS) == {
        "data": {"values": [1, 2, 3], "now": 37},
        "title": "@ x",
    }


def test_unsourced_numbers_flags_typed_measurements_only() -> None:
    text = "Deploys rose 42% to {{delivery.deploys}} in 2026, the 95th percentile, a 30-day window."
    assert unsourced_numbers(text) == ["42%"]
