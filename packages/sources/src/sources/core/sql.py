"""The SQL guard: one read-only statement with named parameters, checked before it runs.

A statement passes when, outside its string literals, quoted names and comments, it
holds one `SELECT` or `WITH` statement, no write keyword, no function with side effects,
no backslash (a psql command) and only the named parameters it is given. The database
session is read-only as well; the guard stops a write before a connection opens.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from sources.core.collect import RequestError, Result, only
from sources.core.periods import Window

MAX_SQL = 2000
MAX_ROWS = 10_000
TIMEOUT_SECONDS = 30
WINDOW_PARAMS = ("start", "end", "until")
PARAM = re.compile(r"(?<![:\w]):([A-Za-z_][A-Za-z0-9_]*)")
NAME = re.compile(r"^[a-z_][a-z0-9_]{0,31}$")
WRITES = re.compile(
    r"\b(insert|update|delete|merge|upsert|truncate|create|alter|drop|rename|grant|revoke|"
    r"copy|call|exec|execute|do|vacuum|reindex|cluster|lock|into|refresh|optimize|restore|"
    r"undrop|msck)\b",
    re.IGNORECASE,
)
SHARE_LOCK = re.compile(r"\bfor\s+(key\s+)?share\b", re.IGNORECASE)
EFFECTS = re.compile(
    r"\b(set_config|pg_terminate_backend|pg_cancel_backend|pg_reload_conf|pg_rotate_logfile|"
    r"pg_switch_wal|pg_create_restore_point|lo_\w+|pg_\w*advisory\w*|pg_read_\w*file|pg_ls_\w+|"
    r"pg_stat_file|dblink\w*|nextval|setval|http_request|read_files|dbms_\w+|utl_\w+)\b",
    re.IGNORECASE,
)
DOLLAR_QUOTE = re.compile(r"\$[A-Za-z_0-9]*\$")


class SqlError(ValueError):
    """A statement the guard refuses, or a result too large to keep, with what to change."""


@dataclass(frozen=True)
class Segment:
    kind: str  # code, string, name or comment
    text: str


def _close(sql: str, i: int, quote: str) -> int:
    """The index after the quote that closes the literal opened at `i`; doubled quotes escape."""
    j = i + 1
    while True:
        k = sql.find(quote, j)
        if k < 0:
            raise SqlError("a quoted string or name is never closed")
        if sql.startswith(quote * 2, k):
            j = k + 2
            continue
        return k + 1


def scan(sql: str) -> list[Segment]:
    """Split a statement into code, string literals, quoted names and comments."""
    out: list[Segment] = []
    code: list[str] = []
    i, n = 0, len(sql)

    def flush() -> None:
        if code:
            out.append(Segment("code", "".join(code)))
            code.clear()

    while i < n:
        if sql.startswith("--", i):
            j = sql.find("\n", i)
            j = n if j < 0 else j
            flush()
            out.append(Segment("comment", sql[i:j]))
            i = j
        elif sql.startswith("/*", i):
            j = sql.find("*/", i + 2)
            if j < 0:
                raise SqlError("a /* comment is never closed")
            flush()
            out.append(Segment("comment", sql[i : j + 2]))
            i = j + 2
        elif sql[i] in "'\"":
            if sql[i] == "'" and re.search(r"(^|[^\w])[nN]?[qQ]$", "".join(code)):
                raise SqlError("Oracle q'...' quoting is not allowed; use plain single quotes")
            j = _close(sql, i, sql[i])
            flush()
            out.append(Segment("string" if sql[i] == "'" else "name", sql[i:j]))
            i = j
        elif sql[i] == "$" and DOLLAR_QUOTE.match(sql, i):
            raise SqlError("dollar quoting ($$) is not allowed; use plain single quotes")
        else:
            code.append(sql[i])
            i += 1
    flush()
    return out


def check(sql: str, params: Mapping[str, Any]) -> list[str]:
    """Refuse anything but one read-only statement; return the parameters it uses, in order."""
    if not sql.strip() or len(sql) > MAX_SQL:
        raise SqlError(f"the statement must hold 1 to {MAX_SQL} characters")
    if "\\" in sql:
        raise SqlError("backslashes are not allowed: they start psql commands")
    segments = scan(sql)
    code = " ".join(s.text for s in segments if s.kind == "code")
    if "*/" in code:
        raise SqlError("a */ has no opening /*; nested comments are not allowed")
    body = code.strip()
    if body.endswith(";"):
        body = body[:-1]
    if ";" in body:
        raise SqlError("one statement only: remove every ; but a final one")
    first = re.match(r"\s*\(*\s*(\w+)", body)
    if not first or first.group(1).lower() not in ("select", "with"):
        raise SqlError("the statement must start with SELECT or WITH")
    for pattern, what in ((WRITES, "write keyword"), (SHARE_LOCK, "row lock")):
        if found := pattern.search(body):
            raise SqlError(
                f"{what} {found.group(0).upper()!r} is not allowed in a read-only query; "
                "put a column with that name in double quotes"
            )
    if found := EFFECTS.search(body):
        raise SqlError(f"{found.group(1)} has side effects and is not allowed")
    used = list(dict.fromkeys(PARAM.findall(body)))
    unknown = [name for name in used if name not in params]
    if unknown:
        raise SqlError(
            f"unknown parameter :{unknown[0]}; the window gives :start, :end and :until, "
            "and request.params names the rest"
        )
    return used


def rebuild(sql: str, param: str = ":{}") -> str:
    """The statement on one line, without comments or a final ;, parameters rewritten.

    `param` formats each parameter name: psql takes `:'{}'`, Oracle and Databricks `:{}`.
    A string literal that spans lines is refused, so the one line stays one statement.
    """
    parts: list[str] = []
    for segment in scan(sql):
        if segment.kind == "comment":
            parts.append(" ")
        elif segment.kind == "code":
            text = PARAM.sub(lambda m: param.format(m.group(1)), segment.text)
            parts.append(re.sub(r"\s+", " ", text))
        else:
            if "\n" in segment.text or "\r" in segment.text:
                raise SqlError("a quoted string spans lines; keep each on one line")
            parts.append(segment.text)
    line = re.sub(r"\s+", " ", "".join(parts)).strip()
    return line[:-1].rstrip() if line.endswith(";") else line


def window_params(span: Window) -> dict[str, str]:
    """`:start` and `:end` are the window's first and last days; `:until` is the day after."""
    return {
        "start": span.start.isoformat(),
        "end": span.end.isoformat(),
        "until": span.until.isoformat(),
    }


def params(raw: Any, window: Mapping[str, str]) -> dict[str, str]:
    """The window's parameters plus the request's own, as text."""
    out = dict(window)
    if raw is None:
        return out
    if not isinstance(raw, Mapping):
        raise SqlError("params must map a name to a value")
    for name, value in raw.items():
        if not NAME.match(str(name)) or name in WINDOW_PARAMS:
            raise SqlError(f"parameter {name!r} must be lowercase and not start, end or until")
        if not isinstance(value, str | int | float) or isinstance(value, bool):
            raise SqlError(f"parameter {name} must be text or a number")
        text = str(value)
        if len(text) > 200 or any(c in text for c in "\n\r\0"):
            raise SqlError(f"parameter {name} must be one line of at most 200 characters")
        out[str(name)] = text
    return out


def tidy(value: Any) -> Any:
    """A value from a result row: midnight timestamps become dates; the rest stays."""
    if isinstance(value, str):
        match = re.match(r"^(\d{4}-\d{2}-\d{2})[ T]00:00:00(\.0+)?(Z|[+-]00(:?00)?)?$", value)
        if match:
            return match.group(1)
    return value


def cap(count: int) -> None:
    """Raise when a result passes the row cap, so every lane words the limit the same way."""
    if count > MAX_ROWS:
        raise SqlError(f"the query returned more than {MAX_ROWS:,} rows; aggregate in SQL")


def columns(rows: Iterable[Mapping[str, Any]], names: list[str]) -> dict[str, list[Any]]:
    """Rows as one list per column, refusing more than 10,000 rows."""
    table: dict[str, list[Any]] = {name: [] for name in names}
    for count, row in enumerate(rows, start=1):
        cap(count)
        for name in names:
            table[name].append(tidy(row.get(name)))
    return table


def result(statement: str, rows: list[dict[str, Any]]) -> Result:
    """One value for a single cell; otherwise one list per column."""
    names = list(rows[0]) if rows else []
    table = columns(rows, names)
    if len(names) == 1 and len(rows) == 1:
        return Result(rebuild(statement), value=table[names[0]][0])
    warnings = [] if rows else ["the query returned no rows"]
    return Result(rebuild(statement), table=table, warnings=warnings)


def read(
    request: Mapping[str, Any],
    span: Window,
    runner: Callable[[str, dict[str, str]], list[dict[str, Any]]],
) -> Result:
    """The script lane's read: check the request, bind the window, run the statement."""
    only(request, {"sql", "params"})
    statement = request.get("sql")
    if not isinstance(statement, str):
        raise RequestError("request.sql must be the statement")
    values = params(request.get("params"), window_params(span))
    return result(statement, runner(statement, values))
