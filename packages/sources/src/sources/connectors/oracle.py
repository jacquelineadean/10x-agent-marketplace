"""Oracle for the script lane, through the user's own SQLcl (`sql`).

SQLcl gets an argument list and a script on standard input, never a shell. The script
connects, binds the named parameters, runs `SET TRANSACTION READ ONLY` and the statement
on one line, capped at 10,001 rows, and prints the rows as JSON. The password travels on
standard input only. SQLcl runs under a 45-second limit: its start-up plus the 30-second
statement budget.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Mapping
from typing import Any

from sources.connectors.errors import SourceError
from sources.connectors.wire import Wire
from sources.core import sql
from sources.core.collect import RequestError, Result, only
from sources.core.periods import Window
from sources.core.reach import Reach, ReachError

USER = re.compile(r"^[A-Za-z][A-Za-z0-9_$#]{0,127}$")
DSN = re.compile(r"^[A-Za-z0-9_.:/@()=,-]{1,512}$")
LIMIT_SECONDS = 45


def _login(reach: Reach) -> str:
    user, password = reach.need("user", "password")
    dsn = f"{reach.host}/{reach.database}" if reach.host else reach.need("dsn")[0]
    if not USER.match(user):
        raise ReachError("the Oracle user must be a plain name")
    if any(c in password for c in '"\n\r\0'):
        raise ReachError("the Oracle password cannot hold a double quote or a line break")
    if not DSN.match(dsn):
        raise ReachError("the Oracle DSN must be host:port/service or a TNS alias, no spaces")
    return f'CONNECT {user}/"{password}"@{dsn}'


def script(statement: str, values: Mapping[str, str], login: str) -> str:
    """The SQLcl script: settings, login, binds, a read-only transaction, the statement."""
    used = sql.check(statement, values)
    binds = []
    for name in used:
        binds.append(f"VARIABLE {name} VARCHAR2(4000)")
        quoted = values[name].replace("'", "''")
        binds.append(f"EXEC :{name} := '{quoted}'")
    line = sql.rebuild(statement)
    return "\n".join(
        [
            "SET DEFINE OFF",
            "SET ECHO OFF",
            "SET FEEDBACK OFF",
            "SET VERIFY OFF",
            "SET SQLFORMAT JSON",
            "WHENEVER SQLERROR EXIT FAILURE ROLLBACK",
            "WHENEVER OSERROR EXIT FAILURE ROLLBACK",
            login,
            *binds,
            "ROLLBACK;",
            "SET TRANSACTION READ ONLY;",
            f"SELECT * FROM ({line}) WHERE ROWNUM <= {sql.MAX_ROWS + 1};",  # noqa: S608  passed sql.check; values are binds
            "ROLLBACK;",
            "EXIT",
            "",
        ]
    )


def rows_of(output: str) -> list[dict[str, Any]]:
    """Rows from SQLcl's JSON output, keyed by lowercase column name in column order."""
    start = output.find("{")
    if start < 0:
        raise SourceError("SQLcl printed no JSON result")
    try:
        data, _ = json.JSONDecoder().raw_decode(output[start:])
        result = data["results"][0]
        names = [str(c["name"]).lower() for c in result.get("columns") or []]
        items = result.get("items") or []
    except (json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise SourceError("SQLcl printed a result in an unexpected shape") from exc
    if len(items) > sql.MAX_ROWS:
        raise sql.SqlError(f"the query returned more than {sql.MAX_ROWS:,} rows; aggregate in SQL")
    return [{n: {k.lower(): v for k, v in item.items()}.get(n) for n in names} for item in items]


def run(
    statement: str, values: Mapping[str, str], reach: Reach, wire: Wire
) -> list[dict[str, Any]]:
    program = wire.which("sql")
    if not program:
        raise SourceError("SQLcl (sql) is not installed; install it or use a connector")
    text = script(statement, values, _login(reach))
    try:
        done = wire.runner(
            [program, "-S", "/nolog"],
            input=text,
            capture_output=True,
            text=True,
            env=dict(wire.environ),
            timeout=LIMIT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise SourceError(f"SQLcl ran past {LIMIT_SECONDS} seconds") from exc
    if done.returncode != 0:
        lines = [x.strip() for x in (done.stdout + "\n" + done.stderr).splitlines() if x.strip()]
        message = next((x for x in lines if x.startswith(("ORA-", "SP2-", "Error"))), "")
        raise SourceError(f"SQLcl failed: {message[:300] or 'see the database log'}")
    return rows_of(done.stdout)


def read(request: Mapping[str, Any], span: Window, reach: Reach, wire: Wire) -> Result:
    only(request, {"sql", "params"})
    statement = request.get("sql")
    if not isinstance(statement, str):
        raise RequestError("request.sql must be the statement")
    values = sql.params(request.get("params"), sql.window_params(span))
    return sql.result(statement, run(statement, values, reach, wire))
