"""digest.md: what Claude reads in place of facts.json, under 12,000 bytes.

One section per system with its lane and dates, then each fact's value and note, each
series' length, ends and range, and the derive table's targets. Code computes the range;
Claude copies nothing from it into a page, which reads facts through tokens.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import date
from typing import Any

from sources.core.contract import covering, facts_of, is_record

LIMIT = 12_000
CELL = 70


def _cell(value: Any) -> str:
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text if len(text) <= CELL else text[: CELL - 1] + "…"


def _number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _row(path: str, node: Any) -> str:
    if is_record(node):
        unit = f" {node['unit']}" if node.get("unit") else ""
        value = _cell(f"{node['value']}{unit}")
        return f"| `{path}` | {value} | {_cell(node.get('note', ''))} |"
    if isinstance(node, list):
        values = [v for v in node if _number(v)]
        span = f"{len(node)} points, {_cell(node[0])} to {_cell(node[-1])}" if node else "empty"
        if values and len(values) == len(node):
            span += f", range {min(values)} to {max(values)}"
        return f"| `{path}` | series | {span} |"
    return f"| `{path}` | {_cell(node)} | |"


def _header(group: str, entries: Mapping[str, Any], paths: list[str]) -> str:
    used = [entries[k] for k in dict.fromkeys(covering(p, entries) for p in paths) if k]
    lanes = sorted({str(e.get("lane", "")) for e in used if isinstance(e, Mapping)})
    via = sorted({str(e.get("connection", "")) for e in used if isinstance(e, Mapping)})
    dates = sorted({str(e.get("as_of", "")) for e in used if isinstance(e, Mapping)})
    when = dates[-1] if len(dates) == 1 else f"{dates[0]} to {dates[-1]}" if dates else "unknown"
    lane = ", ".join(lanes) or "unknown"
    return f"## {group}\nLane {lane} through {', '.join(via) or 'unknown'}; as of {when}.\n"


def render(facts: Mapping[str, Any], queries: Mapping[str, Any], today: date) -> str:
    """The digest; long sections lose rows from the end, with a count of what was cut."""
    entries = queries.get("queries", {}) if isinstance(queries, Mapping) else {}
    groups: dict[str, list[tuple[str, str]]] = {}
    for path, node in facts_of(facts):
        groups.setdefault(path.split(".")[0], []).append((path, _row(path, node)))
    derive = facts.get("derive", {})
    derived = [
        f"| `{_cell(target)}` | {_cell(spec.get('fn', ''))} |"
        for target, spec in (derive.items() if isinstance(derive, Mapping) else [])
        if isinstance(spec, Mapping)
    ]
    count = sum(len(rows) for rows in groups.values())
    head = (
        f"# Digest\nWritten {today.isoformat()}: {count} facts from "
        f"{', '.join(groups) or 'no system'}. Pages read values through tokens; "
        "quote none from here.\n"
    )
    cut: dict[str, int] = {}

    def text() -> str:
        out = head
        for group, rows in groups.items():
            out += "\n" + _header(group, entries, [p for p, _ in rows])
            out += "| Fact | Value | Note |\n| --- | --- | --- |\n"
            out += "".join(row + "\n" for _, row in rows)
            if cut.get(group):
                out += f"{cut[group]} more facts under `{group}` are in facts.json.\n"
        if derived:
            out += "\n## Derived by the build\n| Target | fn |\n| --- | --- |\n"
            out += "".join(row + "\n" for row in derived)
        return out

    while True:
        out = text()
        over = len(out.encode("utf-8")) - LIMIT
        biggest = max(groups, key=lambda g: len(groups[g]), default="")
        if over <= 0 or not biggest or len(groups[biggest]) <= 1:
            return out
        freed = 0
        while freed < over and len(groups[biggest]) > 1:
            freed += len(groups[biggest].pop()[1].encode("utf-8")) + 1
            cut[biggest] = cut.get(biggest, 0) + 1
