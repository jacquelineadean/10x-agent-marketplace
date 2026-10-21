"""Fill the write-up's number tokens from metrics.json and list any number written by hand.

The writer never types a measured number. It writes `{{journeys.fresh-load.speedup}}` and this
module puts in the value, so a number in the post cannot drift from the data.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from perf_ratchet.core.numbers import compact, p_value, pct, plain, speedup, with_unit
from perf_ratchet.core.report import lookup

SOURCES_HEADING = "## Numbers and their sources"
_TOKEN = re.compile(r"\{\{\s*([A-Za-z0-9_.\-]+)\s*(?:\|\s*([a-z:]+)\s*)?\}\}")
_ALLOWED_BARE = re.compile(
    r"\d{4}-\d{2}-\d{2}"  # dates
    r"|\bc-\d{4,}\b"  # change ids
    r"|\bp(?:50|75|90|95|99)\b"  # percentile names
    r"|^\s*\d+\.\s"  # ordered list markers
    r"|\b(?:19|20)\d{2}\b"  # years
    r"|https?://\S+"  # links
    r"|`[^`]*`",  # code spans
    re.MULTILINE,
)
_BARE_NUMBER = re.compile(r"(?<![\w.])(?<!\w-)\d[\d,]*(?:\.\d+)?\s*(?:%|x\b|ms\b|s\b)?")
_VALUE_FIELDS = ("baseline", "current", "previous", "target", "best_day", "before", "after")
_BENCH_FIELDS = ("original", "ceiling", "latest")


@dataclass
class Filled:
    text: str
    used: dict[str, str] = field(default_factory=dict)
    unknown: list[str] = field(default_factory=list)
    bare: list[str] = field(default_factory=list)


def fill(source: str, metrics: dict[str, Any]) -> Filled:
    filled = Filled("")

    def replace(match: re.Match[str]) -> str:
        key, style = match.group(1), match.group(2) or ""
        try:
            value = lookup(metrics, key)
        except KeyError:
            filled.unknown.append(key)
            return f"[MISSING {key}]"
        text = format_value(metrics, key, value, style)
        filled.used[key] = text
        return text

    filled.text = _TOKEN.sub(replace, source)
    filled.bare = bare_numbers(_TOKEN.sub("", source))
    return filled


def format_value(metrics: dict[str, Any], key: str, value: Any, style: str = "") -> str:
    """Choose the format from the filter, else from the key's last part."""
    if value is None:
        return "n/a"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, str):
        return value
    if not isinstance(value, int | float):
        raise ValueError(f"{key} is not a single value")
    last = key.rsplit(".", 1)[-1]
    if style == "pct" or (not style and last.endswith("_pct")):
        return pct(value, signed=False)
    if style == "signed":
        return pct(value)
    if style == "x" or (not style and last.endswith("speedup")):
        return speedup(value)
    if style == "p" or (not style and (last == "p" or last.endswith("_p"))):
        return p_value(value)
    if style == "s":
        return f"{plain(value / 1000)} s"
    if style == "compact":
        return compact(value)
    if style.startswith("unit:"):
        return with_unit(value, style.split(":", 1)[1])
    if style == "num":
        return plain(value)
    unit = _unit_for(metrics, key, last)
    return with_unit(value, unit) if unit else plain(value)


def bare_numbers(text: str) -> list[str]:
    """Numbers typed into prose instead of a token; dates, ids, years and code are allowed."""
    stripped = _ALLOWED_BARE.sub(" ", text)
    stripped = re.sub(r"^#.*$", " ", stripped, flags=re.MULTILINE)
    return [m.group(0).strip() for m in _BARE_NUMBER.finditer(stripped)]


def sources_section(filled: Filled) -> str:
    if not filled.used:
        return ""
    rows = [f"| `{key}` | {value} |" for key, value in sorted(filled.used.items())]
    return "\n".join(
        [
            "",
            SOURCES_HEADING,
            "",
            "Every number above was filled in from metrics.json by perf-ratchet.",
            "",
            "| Key | Value |",
            "| --- | --- |",
            *rows,
            "",
        ]
    )


def _unit_for(metrics: dict[str, Any], key: str, last: str) -> str:
    parts = key.split(".")
    if parts[0] == "journeys" and len(parts) == 3 and last in _VALUE_FIELDS:
        return str(metrics["journeys"][parts[1]]["unit"])
    if parts[0] == "changes" and last in _VALUE_FIELDS:
        try:
            return str(lookup(metrics, ".".join(parts[:-1]) + ".unit"))
        except KeyError:
            return ""
    if parts[0] == "benchmarks" and len(parts) == 3 and last in _BENCH_FIELDS:
        return str(metrics["benchmarks"][parts[1]]["unit"])
    return ""
