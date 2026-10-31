"""Facts: every number on the page, with where it came from.

A story never types a number into its prose. It writes a token such as
`{{delivery.deploys_per_week}}` and the renderer fills in the value from the facts
file, formatted, and wrapped in a span that names its source. Chart blocks point at
series the same way with `"@delivery.weekly"`.

A fact is either a bare value or a record:
    {"value": 71, "unit": "%", "source": "datadog", "note": "share of checkout requests"}
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

TOKEN = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*(?:\|\s*([a-z0-9]+)\s*)?\}\}")
REF = re.compile(r"^@[A-Za-z0-9_.\-]+$")
FORMATS = (
    "auto",
    "int",
    "dec1",
    "dec2",
    "compact",
    "signed",
    "pct",
    "plain",
    "date",
    "month",
    "year",
)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class FactError(ValueError):
    """A token or reference that names no fact, or a value that cannot be formatted."""


@dataclass(frozen=True)
class Fact:
    """One resolved fact."""

    path: str
    value: Any
    unit: str = ""
    source: str = ""
    note: str = ""


def lookup(facts: Mapping[str, Any], path: str) -> Fact:
    """Find a fact by dotted path; raises FactError naming the closest existing key."""
    node: Any = facts
    walked: list[str] = []
    for part in path.split("."):
        if isinstance(node, Mapping) and part in node:
            node = node[part]
            walked.append(part)
            continue
        if isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
            walked.append(part)
            continue
        here = ".".join(walked) or "(top level)"
        options = ", ".join(sorted(node)) if isinstance(node, Mapping) else "no keys"
        raise FactError(f"no fact {path!r}: {here} has {options}")
    if isinstance(node, Mapping) and "value" in node:
        return Fact(
            path=path,
            value=node["value"],
            unit=str(node.get("unit", "")),
            source=str(node.get("source", "")),
            note=str(node.get("note", "")),
        )
    return Fact(path=path, value=node)


def resolve_refs(spec: Any, facts: Mapping[str, Any]) -> Any:
    """Replace every "@path" string inside a block spec with the raw fact value."""
    if isinstance(spec, str) and REF.match(spec):
        return lookup(facts, spec[1:]).value
    if isinstance(spec, Mapping):
        return {k: resolve_refs(v, facts) for k, v in spec.items()}
    if isinstance(spec, list):
        return [resolve_refs(v, facts) for v in spec]
    return spec


def fill(text: str, facts: Mapping[str, Any]) -> str:
    """Text with every token replaced by its formatted value, for places with no hover."""

    def one(m: re.Match[str]) -> str:
        found = lookup(facts, m.group(1))
        return format_value(found.value, found.unit, m.group(2) or "auto")

    return TOKEN.sub(one, text)


def format_value(value: Any, unit: str = "", fmt: str = "auto") -> str:
    """Format a fact for prose: thousands separators, units, compact money, dates."""
    if fmt not in FORMATS:
        raise FactError(f"unknown format {fmt!r}; use one of {', '.join(FORMATS)}")
    if fmt in ("date", "month", "year"):
        return _format_date(str(value), fmt)
    if isinstance(value, bool) or not isinstance(value, int | float):
        return str(value)
    if isinstance(value, float) and not math.isfinite(value):
        raise FactError(f"value {value!r} is not a finite number")
    number = float(value)
    if fmt == "pct":
        unit = unit or "%"
    sign = "+" if fmt == "signed" and number > 0 else ""
    if fmt == "signed":
        fmt = "auto"
    if unit == "$" or fmt == "compact":
        if unit not in ("$", ""):
            return sign + _compact(number, money=False) + _unit_suffix(unit, number)
        text = _compact(number, money=unit == "$")
        return sign + text
    if fmt == "plain":
        unit = ""
        fmt = "auto"
    if fmt == "int" or (fmt in ("auto", "pct") and float(number).is_integer()):
        body = f"{round(number):,}"
    elif fmt == "dec1":
        body = f"{number:,.1f}"
    elif fmt == "dec2":
        body = f"{number:,.2f}"
    else:
        body = f"{number:,.3f}".rstrip("0").rstrip(".")
    body = body.replace("-", "−") if number < 0 else body
    return sign + body + _unit_suffix(unit, number)


def _unit_suffix(unit: str, number: float) -> str:
    if not unit:
        return ""
    if unit in ("%", "x", "×"):
        return "%" if unit == "%" else "×"
    if unit in ("pts", "pp"):
        return f" {unit}"
    singular = {
        "days": "day",
        "hours": "hour",
        "minutes": "minute",
        "weeks": "week",
        "sprints": "sprint",
        "engineers": "engineer",
        "services": "service",
    }
    if abs(number) == 1 and unit in singular:
        return f" {singular[unit]}"
    return f" {unit}"


def _compact(number: float, money: bool) -> str:
    prefix = "$" if money else ""
    sign = "−" if number < 0 else ""
    n = abs(number)
    for limit, suffix in ((1e9, "B"), (1e6, "M"), (1e3, "K")):
        if n >= limit:
            scaled = n / limit
            digits = 0 if scaled >= 100 else 1
            text = f"{scaled:.{digits}f}"
            if digits:
                text = text.rstrip("0").rstrip(".")
            return f"{sign}{prefix}{text}{suffix}"
    text = f"{n:,.0f}" if n >= 10 or n == int(n) else f"{n:,.1f}"
    return f"{sign}{prefix}{text}"


def _format_date(text: str, fmt: str) -> str:
    try:
        parts = [int(p) for p in text.split("-")]
    except ValueError as exc:
        raise FactError(f"{text!r} is not an ISO date like 2026-10-14") from exc
    if not parts or not 1 <= len(parts) <= 3:
        raise FactError(f"{text!r} is not an ISO date like 2026-10-14")
    year = parts[0]
    if fmt == "year" or len(parts) == 1:
        return str(year)
    month = MONTHS[parts[1] - 1] if 1 <= parts[1] <= 12 else None
    if month is None:
        raise FactError(f"{text!r} has no month {parts[1]}")
    if fmt == "month" or len(parts) == 2:
        return f"{month} {year}"
    try:
        day = date(year, parts[1], parts[2]).day
    except ValueError as exc:
        raise FactError(f"{text!r} is not a real date") from exc
    return f"{day} {month} {year}"


# A number followed by a letter or hyphen ("95th", "30-day", "3PL") names a thing, not a
# measurement, so it is not flagged.
UNSOURCED = re.compile(
    r"(?<![\w#.])[−\-+]?\$?\d(?:[\d,]*\d)?(?:\.\d+)?(?![\w-])\s?(?:%|×|[KMB]\b)?"
)
YEAR = re.compile(r"^(19|20)\d\d$")


def unsourced_numbers(text: str) -> list[str]:
    """Numbers typed straight into prose instead of a token; years are allowed."""
    stripped = TOKEN.sub(" ", text)
    found = []
    for match in UNSOURCED.finditer(stripped):
        raw = match.group(0).strip()
        if YEAR.match(raw) or raw in ("0", "1"):
            continue
        found.append(raw)
    return found
