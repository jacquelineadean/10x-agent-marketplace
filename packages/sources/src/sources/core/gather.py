"""The script lane's bookkeeping: which entries to run, and where their results go.

An entry in `queries.json` with `"lane": "script"` names a fact path under its system
(`jira.resolved`), a `request` and a `window`. Gathering writes the result at that path
in `facts.json` (one value as a record, a table as one list per column) and stamps the
entry with the query text, the window read and the as-of date.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from typing import Any

from sources.core.collect import RequestError, Result
from sources.core.periods import Window, window
from sources.core.systems import BY_ID


def script_entries(queries: Mapping[str, Any], paths: Iterable[str] = ()) -> list[str]:
    """Paths of the script-lane entries, all of them or the ones named."""
    entries = queries.get("queries") if isinstance(queries, Mapping) else None
    if not isinstance(entries, Mapping):
        raise RequestError("queries.json must hold {'schema_version': 1, 'queries': {...}}")
    wanted = set(paths)
    unknown = sorted(wanted - set(entries))
    if unknown:
        raise RequestError(f"queries.json has no entry {unknown[0]}")
    return [
        str(path)
        for path, entry in entries.items()
        if isinstance(entry, Mapping)
        and entry.get("lane") == "script"
        and (not wanted or path in wanted)
    ]


def parts(path: str, entry: Mapping[str, Any]) -> tuple[str, Mapping[str, Any], Window]:
    """The system, request and window of a script entry, checked."""
    system = path.split(".")[0]
    if system not in BY_ID or path.count(".") < 1:
        raise RequestError(f"{path}: a script entry names a fact under a system, such as jira.done")
    if entry.get("system") != system:
        raise RequestError(f"{path}: system must be {system!r}")
    request = entry.get("request")
    if not isinstance(request, Mapping):
        raise RequestError(f"{path}: a script entry needs a request object")
    return system, request, window(entry.get("window"))


def place(
    facts: dict[str, Any], path: str, result: Result, request: Mapping[str, Any], span: Window
) -> bool:
    """Write a result into facts at `path`; False when there was no value to write."""
    system, *rest = path.split(".")
    node = facts.setdefault(system, {})
    for key in rest[:-1]:
        child = node.setdefault(key, {})
        if not isinstance(child, dict) or "value" in child:
            raise RequestError(f"{path} runs through {key}, which holds a value")
        node = child
    if result.table is not None:
        node[rest[-1]] = result.table
        return True
    if result.value is None:
        node.pop(rest[-1], None)
        return False
    record: dict[str, Any] = {"value": result.value, "source": system}
    if request.get("unit"):
        record["unit"] = str(request["unit"])
    # The window goes in the note, so a refresh that moves the window keeps the note true.
    shown = span.text()
    note = str(request.get("note") or "").strip()[: 88 - len(shown)]
    record["note"] = f"{note}, {shown}" if note else f"over {shown}"
    node[rest[-1]] = record
    return True


def stamp(entry: Mapping[str, Any], result: Result, span: Window, as_of: date) -> dict[str, Any]:
    """The entry after a run: the query as run, the window read and the as-of date."""
    return {
        **entry,
        "query": result.query[:2000],
        "window": span.as_json(),
        "as_of": as_of.isoformat(),
    }
