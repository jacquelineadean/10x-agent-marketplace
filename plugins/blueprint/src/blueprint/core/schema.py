"""An `erd` object from a schema export: one row per column, with its key and reference.

The export comes from the reference's `information_schema` query, run by the user or the
sources gatherer; this module only reshapes its rows.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

COLUMNS = ("table", "column", "type", "key", "references")


def erd(rows: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    """Entities in first-seen order, their columns, and a relation per foreign key."""
    entities: dict[str, list[dict[str, str]]] = {}
    relations: list[dict[str, str]] = []
    for row in rows:
        table, column = row.get("table", "").strip(), row.get("column", "").strip()
        if not table or not column:
            continue
        key = row.get("key", "").strip().lower()
        entry = {"name": column, "type": row.get("type", "").strip()}
        if key in ("pk", "fk"):
            entry["key"] = key
        entities.setdefault(table, []).append(entry)
        target = row.get("references", "").strip()
        if target:
            relations.append({"from": f"{table}.{column}", "to": target, "kind": "many-to-one"})
    known = {f"{t}.{c['name']}" for t, cols in entities.items() for c in cols}
    return {
        "entities": [{"id": t, "columns": cols} for t, cols in entities.items()],
        "relations": [r for r in relations if r["to"] in known],
    }
