"""blueprint's commands and its check: `schema` turns a schema export, or a live read of
a Postgres or Oracle catalog, into an `erd` object; `lineage` turns a Databricks table's
lineage into a TAD animation; `sources` runs the linked sources command."""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any

from chronicle_engine import registry
from chronicle_engine.connectors.files import store
from sources.config import settings
from sources.connectors.errors import SourceError
from sources.connectors.files import store as source_store
from sources.connectors.wire import Wire
from sources.core import connections, reach, sql
from sources.core.periods import Window

from blueprint.core import checks, lineage, schema

FAILURES = (SourceError, sql.SqlError, reach.ReachError, connections.ConnectionsError)


def check(checked: registry.Checked) -> None:
    """blueprint's checks, over the story and the animation files the engine read."""
    checks.architecture(checked.story, checked.files, checked.report)
    checks.links(checked.story, checked.report)


def schema_parser(sub: Any) -> None:
    p = sub.add_parser("schema", help="an erd object from a schema export or a live read")
    p.add_argument(
        "export", type=Path, nargs="?", help=f"CSV with columns {', '.join(schema.COLUMNS)}"
    )
    p.add_argument("--connection", help="read the catalog live: postgres, oracle or a name")
    p.add_argument("--schema", help="the schema (Postgres, default public) or owner (Oracle)")
    p.add_argument("--out", type=Path, help="write the erd object here (default: print it)")


def _where(name: str) -> tuple[reach.Reach, Wire]:
    """The Reach for a connection name or system id, with the process environment."""
    wire = Wire(environ=settings.environ())
    named = connections.parse(
        source_store.read_json_or(settings.connections_path(wire.environ), {})
    )
    system = named[name].system if name in named else name
    return reach.reach(system, name, named, wire.environ), wire


def _live_rows(name: str, owner: str | None) -> list[dict[str, Any]]:
    from sources.connectors.collectors import RUNNERS

    where, wire = _where(name)
    run = RUNNERS.get(where.system)
    if run is None:
        raise reach.ReachError(f"schema reads postgres or oracle; {name} is {where.system}")
    default = "public" if where.system == "postgres" else where.key("user").upper()
    rows = run(schema.QUERIES[where.system], {"schema": owner or default}, where, wire)
    return [{k: str(v or "") for k, v in row.items()} for row in rows]


def schema_run(args: argparse.Namespace) -> int:
    if (args.export is None) == (args.connection is None):
        print("error: give a CSV export or --connection, not both", file=sys.stderr)
        return 1
    try:
        rows = (
            _live_rows(args.connection, args.schema)
            if args.connection
            else list(csv.DictReader(io.StringIO(store.read_text(args.export))))
        )
    except FAILURES as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    data = schema.erd(rows)
    text = json.dumps(data, indent=1) + "\n"
    if args.out:
        store.write_text(args.out, text)
        print(
            f"wrote {args.out}: {len(data['entities'])} tables, {len(data['relations'])} relations"
        )
    else:
        print(text, end="")
    return 0


def lineage_parser(sub: Any) -> None:
    p = sub.add_parser("lineage", help="a TAD animation of a Databricks table's lineage")
    p.add_argument("table", help="catalog.schema.table")
    p.add_argument("--connection", default="databricks", help="databricks or a named one")
    p.add_argument("--out", type=Path, required=True, help="the animation.json to write")


def lineage_run(args: argparse.Namespace) -> int:
    try:
        where, wire = _where(args.connection)
        if where.system != "databricks":
            raise reach.ReachError(f"lineage reads databricks; {args.connection} is {where.system}")
        today = date.today()
        from sources.connectors import databricks

        found = databricks.read({"lineage": args.table}, Window(today, today), where, wire)
    except FAILURES as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    table = found.table or {}
    data = lineage.animation(
        args.table, table.get("upstream", []), table.get("downstream", []), today.isoformat()
    )
    store.write_json(args.out, data)
    print(
        f"wrote {args.out}: {len(table.get('upstream', []))} upstream and "
        f"{len(table.get('downstream', []))} downstream tables; next: animate check, then build"
    )
    return 0
