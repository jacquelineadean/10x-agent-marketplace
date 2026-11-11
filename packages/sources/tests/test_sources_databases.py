"""psql and SQLcl as the collectors start them: argument lists, sessions, scripts, rows."""

from __future__ import annotations

import subprocess
from dataclasses import replace
from datetime import date

import pytest
from sources.connectors import oracle, postgres
from sources.connectors.errors import SourceError
from sources.core.periods import Window
from sources.core.reach import ReachError, reach
from sources.core.sql import SqlError
from sources_helpers import FakeProgram, text_fixture, wire

Q3 = Window(date(2026, 7, 1), date(2026, 9, 30))
MONTHLY = {
    "sql": "SELECT month, orders, revenue, first FROM monthly\n"
    "WHERE day >= :start AND kind = :kind",
    "params": {"kind": "paid"},
}


def test_psql_gets_an_argument_list_a_read_only_session_and_no_password() -> None:
    program = FakeProgram(stdout=text_fixture("postgres/rows.json"))
    where = reach(
        "postgres",
        "postgres",
        {},
        {"DATABASE_URL": "postgresql://reader:s%40cret@db:5433/shop?sslmode=require"},
    )
    result = postgres.read(
        MONTHLY, Q3, where, wire(program=program, PGOPTIONS="-c search_path=sales")
    )
    assert result.table == {
        "month": ["2026-07", "2026-08", "2026-09"],
        "orders": [905, 905, 875],
        "revenue": [44964.95, 43808.95, 42842.25],
        "first": ["2026-07-01", "2026-08-01", None],
    }
    call = program.calls[0]
    assert call["argv"] == [
        "/usr/bin/psql",
        "--no-psqlrc",
        "--quiet",
        "--no-align",
        "--tuples-only",
        "--set",
        "ON_ERROR_STOP=1",
        "--set",
        "start=2026-07-01",
        "--set",
        "kind=paid",
    ]
    assert "s@cret" not in " ".join(call["argv"])
    env = call["env"]
    assert (env["PGHOST"], env["PGPORT"], env["PGDATABASE"]) == ("db", "5433", "shop")
    assert (env["PGUSER"], env["PGPASSWORD"], env["PGSSLMODE"]) == ("reader", "s@cret", "require")
    assert env["PGOPTIONS"] == (
        "-c search_path=sales -c default_transaction_read_only=on -c statement_timeout=30s"
    )
    assert call["input"] == (
        "SELECT coalesce(json_agg(sources_q), '[]'::json) FROM (SELECT * FROM (SELECT month, "
        "orders, revenue, first FROM monthly WHERE day >= :'start' AND kind = :'kind') AS "
        "sources_inner LIMIT 10001) AS sources_q;\n"
    )
    assert call["timeout"] == 40 and "shell" not in call


def test_psql_errors_timeouts_and_a_missing_program_are_reported() -> None:
    where = reach("postgres", "postgres", {}, {"DATABASE_URL": "postgresql://r@db/shop"})
    failing = FakeProgram(
        returncode=3, stderr="ERROR:  cannot execute INSERT in a read-only transaction\n"
    )
    with pytest.raises(SourceError, match="read-only transaction"):
        postgres.read({"sql": "SELECT bump()"}, Q3, where, wire(program=failing))

    def slow(argv: list[str], **options: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(argv, 40)

    with pytest.raises(SourceError, match="30 seconds"):
        postgres.read({"sql": "SELECT pg_sleep(60)"}, Q3, where, replace(wire(), runner=slow))
    missing = replace(wire(), which=lambda name: None)
    with pytest.raises(SourceError, match="psql is not installed"):
        postgres.read({"sql": "SELECT 1"}, Q3, where, missing)
    program = FakeProgram()
    with pytest.raises(SqlError, match="INSERT"):
        postgres.read(
            {"sql": "WITH x AS (INSERT INTO t VALUES (1)) SELECT 1"},
            Q3,
            where,
            wire(program=program),
        )
    assert program.calls == []
    with pytest.raises(ReachError, match="postgres://"):
        postgres.read(
            {"sql": "SELECT 1"},
            Q3,
            reach("postgres", "postgres", {}, {"DATABASE_URL": "mysql://x"}),
            wire(),
        )


def test_sqlcl_runs_a_read_only_script_with_binds_and_the_password_on_stdin_only() -> None:
    program = FakeProgram(stdout=text_fixture("oracle/sqlcl.txt"))
    environ = {
        "ORACLE_USER": "REPORTS",
        "ORACLE_PASSWORD": "p@ss/w'rd",
        "ORACLE_DSN": "db.acme:1521/ORCLPDB1",
    }
    request = {
        "sql": "SELECT month, orders, first_day FROM monthly -- per month\n"
        "WHERE day >= TO_DATE(:start, 'YYYY-MM-DD') AND kind = :kind",
        "params": {"kind": "o'brien"},
    }
    result = oracle.read(request, Q3, reach("oracle", "oracle", {}, environ), wire(program=program))
    assert result.table == {
        "month": ["2026-07", "2026-08"],
        "orders": [905, 905],
        "first_day": ["2026-07-01", "2026-08-01"],
    }
    call = program.calls[0]
    assert call["argv"] == ["/usr/bin/sql", "-S", "/nolog"]
    assert call["timeout"] == 45
    lines = call["input"].splitlines()
    assert lines[7] == 'CONNECT REPORTS/"p@ss/w\'rd"@db.acme:1521/ORCLPDB1'
    assert "VARIABLE kind VARCHAR2(4000)" in lines and "EXEC :kind := 'o''brien'" in lines
    assert lines.index("SET TRANSACTION READ ONLY;") < lines.index(
        "SELECT * FROM (SELECT month, orders, first_day FROM monthly WHERE day >= "
        "TO_DATE(:start, 'YYYY-MM-DD') AND kind = :kind) WHERE ROWNUM <= 10001;"
    )
    assert "p@ss" not in " ".join(call["argv"])


def test_sqlcl_refuses_unsafe_logins_and_reports_ora_errors() -> None:
    bad = {"ORACLE_USER": "R", "ORACLE_PASSWORD": 'a"b', "ORACLE_DSN": "db/x"}
    with pytest.raises(ReachError, match="double quote"):
        oracle.read({"sql": "SELECT 1 FROM dual"}, Q3, reach("oracle", "oracle", {}, bad), wire())
    spaced = {**bad, "ORACLE_PASSWORD": "ok", "ORACLE_DSN": "db x"}
    with pytest.raises(ReachError, match="no spaces"):
        oracle.read(
            {"sql": "SELECT 1 FROM dual"}, Q3, reach("oracle", "oracle", {}, spaced), wire()
        )
    fine = {**bad, "ORACLE_PASSWORD": "ok"}
    failing = FakeProgram(returncode=1, stdout="ORA-00942: table or view does not exist\n")
    with pytest.raises(SourceError, match="ORA-00942"):
        oracle.read(
            {"sql": "SELECT 1 FROM nope"},
            Q3,
            reach("oracle", "oracle", {}, fine),
            wire(program=failing),
        )
    with pytest.raises(SourceError, match="no JSON"):
        oracle.rows_of("Connected.\n")
