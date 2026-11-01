"""An `erd` object from a schema export: one row per column, with its key and reference.

The rows come from a CSV export of the reference's `information_schema` query, or from
`blueprint schema --connection`, which runs the query below through the sources
package's psql or SQLcl collector; this module only holds the queries and reshapes rows.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

COLUMNS = ("table", "column", "type", "key", "references")
# One row per column with its key and the column a foreign key points at; :schema names
# the schema (Postgres) or owner (Oracle). Both read catalog views only. Postgres reads
# pg_catalog: information_schema hides constraints from a role that may only SELECT.
QUERIES = {
    "postgres": """
SELECT c.relname AS "table", a.attname AS "column",
       format_type(a.atttypid, a.atttypmod) AS "type",
       CASE WHEN pk.conname IS NOT NULL THEN 'pk'
            WHEN fk.conname IS NOT NULL THEN 'fk' ELSE '' END AS "key",
       CASE WHEN fk.conname IS NOT NULL THEN rt.relname || '.' || ra.attname
            ELSE '' END AS "references"
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_constraint pk
  ON pk.conrelid = c.oid AND pk.contype = 'p' AND a.attnum = ANY (pk.conkey)
LEFT JOIN pg_constraint fk
  ON fk.conrelid = c.oid AND fk.contype = 'f' AND a.attnum = ANY (fk.conkey)
LEFT JOIN pg_class rt ON rt.oid = fk.confrelid
LEFT JOIN pg_attribute ra
  ON ra.attrelid = fk.confrelid AND ra.attnum = fk.confkey[array_position(fk.conkey, a.attnum)]
WHERE n.nspname = :schema AND c.relkind IN ('r', 'p', 'v', 'm')
ORDER BY c.relname, a.attnum
""",
    "oracle": """
SELECT c.table_name AS "table", c.column_name AS "column", c.data_type AS "type",
       CASE WHEN pk.column_name IS NOT NULL THEN 'pk'
            WHEN fk.column_name IS NOT NULL THEN 'fk' ELSE '' END AS "key",
       CASE WHEN fk.column_name IS NOT NULL
            THEN fk.r_table || '.' || fk.r_column ELSE '' END AS "references"
FROM all_tab_columns c
LEFT JOIN (SELECT cc.owner, cc.table_name, cc.column_name
           FROM all_cons_columns cc JOIN all_constraints k
             ON k.owner = cc.owner AND k.constraint_name = cc.constraint_name
           WHERE k.constraint_type = 'P') pk
  ON pk.owner = c.owner AND pk.table_name = c.table_name AND pk.column_name = c.column_name
LEFT JOIN (SELECT cc.owner, cc.table_name, cc.column_name,
                  rc.table_name AS r_table, rcc.column_name AS r_column
           FROM all_cons_columns cc
           JOIN all_constraints k ON k.owner = cc.owner AND k.constraint_name = cc.constraint_name
           JOIN all_constraints rc
             ON rc.owner = k.r_owner AND rc.constraint_name = k.r_constraint_name
           JOIN all_cons_columns rcc ON rcc.owner = rc.owner
            AND rcc.constraint_name = rc.constraint_name AND rcc.position = cc.position
           WHERE k.constraint_type = 'R') fk
  ON fk.owner = c.owner AND fk.table_name = c.table_name AND fk.column_name = c.column_name
WHERE c.owner = :schema
ORDER BY c.table_name, c.column_id
""",
}


# Postgres spells some types out; the short names fit a table's width.
SHORT = {
    "timestamp with time zone": "timestamptz",
    "timestamp without time zone": "timestamp",
    "time with time zone": "timetz",
    "time without time zone": "time",
    "character varying": "varchar",
    "double precision": "float8",
}


def _short(kind: str) -> str:
    for long, short in SHORT.items():
        if kind.startswith(long):
            return short + kind[len(long) :]
    return kind


def erd(rows: Iterable[Mapping[str, str]]) -> dict[str, Any]:
    """Entities in first-seen order, their columns, and a relation per foreign key."""
    entities: dict[str, list[dict[str, str]]] = {}
    relations: list[dict[str, str]] = []
    for row in rows:
        table, column = row.get("table", "").strip(), row.get("column", "").strip()
        if not table or not column:
            continue
        key = row.get("key", "").strip().lower()
        entry = {"name": column, "type": _short(row.get("type", "").strip())}
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
