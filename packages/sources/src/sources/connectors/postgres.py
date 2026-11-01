"""Postgres for the script lane, through the user's own `psql`.

psql gets an argument list and the statement on standard input, never a shell. The
session is read-only (`default_transaction_read_only`) with a 30-second statement
timeout, set through `PGOPTIONS`. Postgres returns the rows as one JSON array, capped
at 10,001 rows, so each value keeps its type. Credentials travel in libpq's own
environment variables, never in the argument list.
"""

from __future__ import annotations

import json
import subprocess
import urllib.parse
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.wire import Wire
from sources.core import sql
from sources.core.collect import RequestError, Result, only
from sources.core.periods import Window
from sources.core.reach import Reach, ReachError

WRAP = (
    "SELECT coalesce(json_agg(sources_q), '[]'::json) FROM "
    "(SELECT * FROM ({line}) AS sources_inner LIMIT {limit}) AS sources_q;\n"
)


def libpq_environment(reach: Reach) -> dict[str, str]:
    """PGHOST, PGDATABASE and the rest from a named connection or DATABASE_URL."""
    out: dict[str, str] = {}
    if reach.host:
        host, _, port = reach.host.removeprefix("https://").partition(":")
        out["PGHOST"] = host
        if port:
            out["PGPORT"] = port
        if reach.database:
            out["PGDATABASE"] = reach.database
    elif reach.key("url"):
        url = urllib.parse.urlsplit(reach.key("url"))
        if url.scheme not in ("postgres", "postgresql"):
            raise ReachError("DATABASE_URL must start with postgres:// or postgresql://")
        pairs = {
            "PGHOST": url.hostname or "",
            "PGPORT": str(url.port or ""),
            "PGDATABASE": url.path.lstrip("/"),
            "PGUSER": urllib.parse.unquote(url.username or ""),
            "PGPASSWORD": urllib.parse.unquote(url.password or ""),
            "PGSSLMODE": dict(urllib.parse.parse_qsl(url.query)).get("sslmode", ""),
        }
        out.update({k: v for k, v in pairs.items() if v})
    for role, name in (("user", "PGUSER"), ("password", "PGPASSWORD")):
        if reach.key(role) and name not in out:
            out[name] = reach.key(role)
    return out


def run(
    statement: str, values: Mapping[str, str], reach: Reach, wire: Wire
) -> list[dict[str, Any]]:
    """Rows of a statement that has passed the guard, as objects in column order."""
    psql = wire.which("psql")
    if not psql:
        raise SourceError("psql is not installed; install the PostgreSQL client or use a connector")
    used = sql.check(statement, values)
    script = WRAP.format(line=sql.rebuild(statement, ":'{}'"), limit=sql.MAX_ROWS + 1)
    argv = [psql, "--no-psqlrc", "--quiet", "--no-align", "--tuples-only"]
    argv += ["--set", "ON_ERROR_STOP=1"]
    for name in used:
        argv += ["--set", f"{name}={values[name]}"]
    options = wire.environ.get("PGOPTIONS", "")
    read_only = f"-c default_transaction_read_only=on -c statement_timeout={sql.TIMEOUT_SECONDS}s"
    environment = {
        **wire.environ,
        **libpq_environment(reach),
        "PGOPTIONS": f"{options} {read_only}".strip(),
        "PGCONNECT_TIMEOUT": "10",
        "PGAPPNAME": "sources",
    }
    try:
        done = wire.runner(
            argv,
            input=script,
            capture_output=True,
            text=True,
            env=environment,
            timeout=sql.TIMEOUT_SECONDS + 10,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"psql ran past {sql.TIMEOUT_SECONDS} seconds") from exc
    if done.returncode != 0:
        lines = [x.strip() for x in done.stderr.splitlines() if x.strip()]
        message = next(
            (x for x in lines if "ERROR" in x or "FATAL" in x), lines[-1] if lines else ""
        )
        raise SourceError(f"psql failed: {message[:300]}")
    try:
        rows = json.loads(done.stdout.strip() or "[]")
    except json.JSONDecodeError as exc:
        raise SourceError("psql printed something other than the JSON rows") from exc
    if len(rows) > sql.MAX_ROWS:
        raise sql.SqlError(f"the query returned more than {sql.MAX_ROWS:,} rows; aggregate in SQL")
    return [dict(row) for row in rows]


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"sql", "params"})
    statement = request.get("sql")
    if not isinstance(statement, str):
        raise RequestError("request.sql must be the statement")
    values = sql.params(request.get("params"), sql.window_params(span))
    return sql.result(statement, run(statement, values, reach, wire))
