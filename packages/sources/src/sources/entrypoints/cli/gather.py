"""`sources gather`: run a run folder's script-lane queries and write facts, queries and digest.

Each entry runs on its own; a failure is reported and the others still run, so a refresh
keeps every number it can get. Output names entries and sizes, never values.
"""

from __future__ import annotations

import sys
from collections.abc import Iterable
from datetime import date
from pathlib import Path
from typing import TextIO

from sources.config import settings
from sources.connectors.collectors import READERS
from sources.connectors.errors import SourceError
from sources.connectors.files import store
from sources.connectors.wire import Wire
from sources.core import connections, contract, digest, gather, periods, reach, sql
from sources.core.collect import RequestError

FAILURES = (
    RequestError,
    periods.PeriodError,
    sql.SqlError,
    reach.ReachError,
    SourceError,
)


def run(
    folder: Path,
    paths: Iterable[str] = (),
    roll: bool = False,
    until: date | None = None,
    wire: Wire | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
    strict: bool = True,
) -> int:
    """Gather into `folder`; 0 when every entry ran and the folder passes the check.

    With `strict` off (a refresh of a folder the gatherer did not write), a folder that
    fails the facts contract keeps its old digest and the run still succeeds.
    """
    out, err = out or sys.stdout, err or sys.stderr
    if until and until > date.today():
        print("error: --until cannot be later than today", file=err)
        return 1
    today = until or date.today()
    wire = wire or Wire(environ=settings.environ())
    facts = store.read_json_or(folder / "facts.json", {})
    queries = store.read_json(folder / "queries.json")
    named = connections.parse(store.read_json_or(settings.connections_path(wire.environ), {}))
    failed: list[str] = []
    for path in gather.script_entries(queries, paths):
        entry = queries["queries"][path]
        try:
            system, request, span = gather.parts(path, entry)
            if roll:
                span = periods.roll(span, str(request.get("per") or "") or None, today)
            where = reach.reach(system, str(entry.get("connection") or system), named, wire.environ)
            result = READERS[system](request, span, where, wire)
            written = gather.place(facts, path, result, request, span)
            queries["queries"][path] = gather.stamp(entry, result, span, today)
        except FAILURES as exc:
            failed.append(path)
            print(f"error: {path}: {exc}", file=err)
            continue
        shown = result.size if written else "no value, left out"
        print(f"{path}: {shown}, {span.text()}, as of {today.isoformat()}", file=out)
        for warning in result.warnings:
            print(f"warning: {path}: {warning}", file=err)
    if roll:
        queries["refreshed"] = today.isoformat()
    store.write_json(folder / "facts.json", facts)
    store.write_json(folder / "queries.json", queries)
    report = contract.check(facts, queries, date.today())
    if report.errors and not strict:
        print(f"note: digest.md not written: {len(report.errors)} contract problems", file=out)
        return 1 if failed else 0
    for line in report.errors:
        print(f"error: {line}", file=err)
    if report.errors:
        return 1
    text = digest.render(facts, queries, today)
    store.write_text(folder / "digest.md", text)
    print(f"wrote {folder / 'digest.md'} ({len(text.encode('utf-8'))} bytes)", file=out)
    return 1 if failed else 0
