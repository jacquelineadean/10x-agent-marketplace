"""Databricks for the script lane: SQL through Statement Execution, and table lineage.

A statement passes the SQL guard, then runs on the named SQL warehouse through the
read-only `sql/statements` POST with a 30-second wait that cancels it, inline JSON rows
and a 10,001-row limit. Lineage is one GET to Unity Catalog's table lineage. The token
should belong to a principal that can only read.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.http import JsonTransport
from sources.connectors.wire import Wire
from sources.core import sql
from sources.core.collect import RequestError, Result, only, text
from sources.core.periods import Window
from sources.core.reach import Reach

STATEMENTS = "/api/2.0/sql/statements"
LINEAGE = "/api/2.0/lineage-tracking/table-lineage"
WAREHOUSE = re.compile(r"^[a-z0-9]{8,32}$")
TABLE = re.compile(r"^[\w-]+\.[\w-]+\.[\w-]+$")
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
INTS = {"BYTE", "SHORT", "INT", "LONG"}
FLOATS = {"FLOAT", "DOUBLE", "DECIMAL"}


def _transport(reach: Reach, wire: Wire) -> JsonTransport:
    (token,) = reach.need("token")
    return JsonTransport(
        "Databricks",
        reach.url(),
        {"Authorization": f"Bearer {token}"},
        read_only_posts=frozenset({STATEMENTS}),
        opener=wire.opener,
        sleeper=wire.sleeper,
    )


def _warehouse(request: Mapping[str, Any], reach: Reach) -> str:
    """The warehouse id from the request, or from the connection's HTTP path."""
    named = str(request.get("warehouse") or reach.path.rstrip("/").rsplit("/", 1)[-1])
    if not WAREHOUSE.match(named):
        raise RequestError(
            "request.warehouse must be the SQL warehouse id, or the connection's path "
            "its HTTP path (/sql/1.0/warehouses/<id>)"
        )
    return named


def _value(raw: Any, kind: str) -> Any:
    if raw is None:
        return None
    if kind in INTS:
        return int(raw)
    if kind in FLOATS:
        return float(raw)
    if kind == "BOOLEAN":
        return str(raw).lower() == "true"
    return sql.tidy(raw)


def _statement(
    request: Mapping[str, Any], span: Window, reach: Reach, transport: JsonTransport
) -> Result:
    statement = request.get("sql")
    if not isinstance(statement, str):
        raise RequestError("request.sql must be the statement")
    values = sql.params(request.get("params"), sql.window_params(span))
    used = sql.check(statement, values)
    line = sql.rebuild(statement)
    body = {
        "warehouse_id": _warehouse(request, reach),
        "statement": line,
        "parameters": [
            {"name": n, "value": values[n], **({"type": "DATE"} if DATE.match(values[n]) else {})}
            for n in used
        ],
        "wait_timeout": f"{sql.TIMEOUT_SECONDS}s",
        "on_wait_timeout": "CANCEL",
        "disposition": "INLINE",
        "format": "JSON_ARRAY",
        "row_limit": sql.MAX_ROWS + 1,
    }
    answer = transport.post_query(STATEMENTS, body)
    if not isinstance(answer, Mapping):
        raise SourceError("Databricks answered without a statement status")
    status = answer.get("status") or {}
    if status.get("state") != "SUCCEEDED":
        message = (status.get("error") or {}).get("message") or "it did not finish in 30 seconds"
        raise SourceError(f"the Databricks statement failed: {str(message)[:300]}")
    manifest = answer.get("manifest") or {}
    if manifest.get("truncated"):
        raise sql.SqlError(f"the query returned more than {sql.MAX_ROWS:,} rows; aggregate in SQL")
    schema = (manifest.get("schema") or {}).get("columns") or []
    names = [str(c["name"]) for c in schema]
    kinds = [str(c.get("type_name", "STRING")) for c in schema]
    rows = list((answer.get("result") or {}).get("data_array") or [])
    link = (answer.get("result") or {}).get("next_chunk_internal_link")
    while link:
        chunk = transport.get(str(link))
        rows += chunk.get("data_array") or []
        link = chunk.get("next_chunk_internal_link")
    table = sql.columns(
        ({n: _value(v, k) for n, v, k in zip(names, row, kinds, strict=False)} for row in rows),
        names,
    )
    if len(names) == 1 and len(rows) == 1:
        return Result(line, value=table[names[0]][0])
    return Result(line, table=table, warnings=[] if rows else ["the query returned no rows"])


def _lineage(request: Mapping[str, Any], transport: JsonTransport) -> Result:
    name = text(request, "lineage", 255)
    if not TABLE.match(name):
        raise RequestError("request.lineage must be catalog.schema.table")
    body = transport.get(LINEAGE, {"table_name": name, "include_entity_lineage": "false"})

    def tables(side: str) -> list[str]:
        found = []
        entries = body.get(side) if isinstance(body, Mapping) else None
        for entry in entries or []:
            info = entry.get("tableInfo") if isinstance(entry, Mapping) else None
            if isinstance(info, Mapping) and info.get("name"):
                found.append(f"{info.get('catalog_name')}.{info.get('schema_name')}.{info['name']}")
        return sorted(dict.fromkeys(found))

    return Result(
        f"GET {LINEAGE}?table_name={name}",
        table={"upstream": tables("upstreams"), "downstream": tables("downstreams")},
    )


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"sql", "params", "warehouse", "lineage"})
    transport = _transport(reach, wire)
    if "lineage" in request:
        return _lineage(request, transport)
    return _statement(request, span, reach, transport)
