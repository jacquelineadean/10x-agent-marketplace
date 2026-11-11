"""The SQL guard: what passes, what it refuses before any connection, and row shaping."""

from __future__ import annotations

import pytest
from sources.core import sql
from sources.core.sql import SqlError

WINDOW = {"start": "2026-07-01", "end": "2026-09-30", "until": "2026-10-01"}


def test_one_select_with_window_parameters_passes_and_names_them_in_order() -> None:
    statement = """
        -- orders per month; DELETE in a comment is fine
        WITH paid AS (SELECT * FROM orders WHERE status = 'paid; DROP TABLE x')
        SELECT date_trunc('month', created_at)::date AS month, count(*) AS "grant"
        FROM paid WHERE created_at >= :start AND created_at < :until
        GROUP BY 1 ORDER BY 1;
    """
    assert sql.check(statement, WINDOW) == ["start", "until"]


@pytest.mark.parametrize(
    ("statement", "message"),
    [
        ("DELETE FROM orders", "start with SELECT or WITH"),
        ("SELECT 1; SELECT 2", "one statement only"),
        ("WITH gone AS (DELETE FROM orders RETURNING id) SELECT count(*) FROM gone", "DELETE"),
        ("SELECT * INTO backup FROM orders", "INTO"),
        ("SELECT * FROM orders FOR UPDATE", "UPDATE"),
        ("SELECT * FROM orders FOR SHARE", "row lock"),
        ("SELECT set_config('transaction_read_only', 'off', false)", "set_config"),
        ("SELECT nextval('orders_id_seq')", "nextval"),
        ("SELECT utl_http.request('http://x') FROM dual", "utl_http"),
        ("SELECT 1 \\! rm -rf ~", "backslashes"),
        ("SELECT $$x$$", "dollar quoting"),
        ("SELECT q'[it's]' FROM dual", "q'...' quoting"),
        ("SELECT 'open", "never closed"),
        ("SELECT 1 /* a /* nested */ */", "nested comments"),
        ("SELECT * FROM t WHERE region = :region", "unknown parameter :region"),
        ("", "1 to 2000 characters"),
    ],
)
def test_the_guard_refuses(statement: str, message: str) -> None:
    with pytest.raises(SqlError, match=message.replace("$", r"\$").replace("[", r"\[")):
        sql.check(statement, WINDOW)


def test_rebuild_puts_the_statement_on_one_line_and_rewrites_parameters_in_code_only() -> None:
    statement = (
        "SELECT count(*) -- how many\nFROM t\nWHERE note = 'a :start b'\n  AND day >= :start;"
    )
    assert sql.rebuild(statement, ":'{}'") == (
        "SELECT count(*) FROM t WHERE note = 'a :start b' AND day >= :'start'"
    )
    assert sql.rebuild("SELECT x::date FROM t WHERE d < :until") == (
        "SELECT x::date FROM t WHERE d < :until"
    )
    with pytest.raises(SqlError, match="spans lines"):
        sql.rebuild("SELECT 'two\nlines'")


def test_params_join_the_window_and_refuse_bad_names_and_values() -> None:
    assert sql.params({"region": "EU", "top": 5}, WINDOW)["top"] == "5"
    for bad in ({"start": "x"}, {"Region": "EU"}, {"r": "a\nb"}, {"r": True}, {"r": ["x"]}):
        with pytest.raises(SqlError):
            sql.params(bad, WINDOW)


def test_rows_become_columns_with_midnight_timestamps_as_dates() -> None:
    rows = [{"day": "2026-07-01T00:00:00+00:00", "n": 3}, {"day": "2026-07-02 13:00:00", "n": 4}]
    assert sql.columns(rows, ["day", "n"]) == {
        "day": ["2026-07-01", "2026-07-02 13:00:00"],
        "n": [3, 4],
    }
    one = sql.result("SELECT count(*) FROM t", [{"count": 7}])
    assert (one.value, one.table) == (7, None)
    with pytest.raises(SqlError, match="more than 10,000 rows"):
        sql.columns(({"n": i} for i in range(10_001)), ["n"])
