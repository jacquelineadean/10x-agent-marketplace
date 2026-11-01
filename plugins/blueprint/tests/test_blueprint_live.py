"""Live reads: `schema --connection` through psql, and `lineage` into a TAD that builds.

psql is a stand-in on PATH that checks what the collector sends and prints recorded rows;
Databricks answers from a recorded lineage reply. No test reaches a database or network.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from blueprint.core import lineage
from blueprint.entrypoints.cli import commands
from blueprint_helpers import run
from sources.connectors.wire import Wire

FAKE_PSQL = """#!/usr/bin/env python3
import json, os, sys
script = sys.stdin.read()
assert "FROM pg_class c" in script and ":'schema'" in script
assert "default_transaction_read_only=on" in os.environ["PGOPTIONS"]
assert "schema=sales" in sys.argv
rows = [
    {"table": "customers", "column": "id", "type": "bigint", "key": "pk", "references": ""},
    {"table": "orders", "column": "id", "type": "bigint", "key": "pk", "references": ""},
    {"table": "orders", "column": "customer_id", "type": "bigint", "key": "fk",
     "references": "customers.id"},
]
print(json.dumps(rows))
"""

LINEAGE = {
    "upstreams": [
        {"tableInfo": {"name": "raw_orders", "catalog_name": "main", "schema_name": "bronze"}},
        {"tableInfo": {"name": "raw_payments", "catalog_name": "main", "schema_name": "bronze"}},
    ],
    "downstreams": [
        {"tableInfo": {"name": "daily_revenue", "catalog_name": "main", "schema_name": "gold"}}
    ],
}


def test_schema_reads_the_catalog_live_through_psql(tmp_path: Path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (bin_dir / "psql").write_text(FAKE_PSQL)
    (bin_dir / "psql").chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "DATABASE_URL": "postgresql://reader:pw@db/shop",
        "SOURCES_CONNECTIONS": str(tmp_path / "none.json"),
    }
    made = run("schema", "--connection", "postgres", "--schema", "sales", env=env)
    assert made.returncode == 0, made.stderr
    data = json.loads(made.stdout)
    assert [e["id"] for e in data["entities"]] == ["customers", "orders"]
    assert data["relations"] == [
        {"from": "orders.customer_id", "to": "customers.id", "kind": "many-to-one"}
    ]
    wrong = run("schema", "--connection", "jira", env=env)
    assert wrong.returncode == 1 and "schema reads postgres or oracle" in wrong.stderr


class _Reply:
    def __init__(self, body: Any) -> None:
        self.status, self._data = 200, json.dumps(body).encode()

    def read(self) -> bytes:
        return self._data

    def __enter__(self) -> _Reply:
        return self

    def __exit__(self, *_: object) -> None:
        return None


def test_lineage_writes_a_tad_that_checks_and_builds(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    seen: list[str] = []

    def opener(request: Any, timeout: float) -> _Reply:
        seen.append(request.full_url)
        return _Reply(LINEAGE)

    environ = {
        "DATABRICKS_HOST": "adb-1.azuredatabricks.net",
        "DATABRICKS_TOKEN": "dapi-test",
        "SOURCES_CONNECTIONS": str(tmp_path / "none.json"),
    }
    monkeypatch.setattr(commands, "Wire", lambda environ: Wire(opener=opener, environ=environ))
    monkeypatch.setattr(commands.settings, "environ", lambda: environ)
    out = tmp_path / "lineage" / "animation.json"
    args = commands.argparse.Namespace(table="main.silver.orders", connection="databricks", out=out)
    assert commands.lineage_run(args) == 0
    assert seen == [
        "https://adb-1.azuredatabricks.net/api/2.0/lineage-tracking/table-lineage"
        "?table_name=main.silver.orders&include_entity_lineage=false"
    ]
    assert "2 upstream and 1 downstream tables" in capsys.readouterr().out
    checked = run("animate", "check", str(out))
    assert checked.returncode == 0, checked.stderr
    built = run("animate", "build", str(out), "--formats", "svg")
    assert built.returncode == 0, built.stderr
    svg = (out.parent / "build" / "animation.svg").read_text()
    assert "raw_payments" in svg and "daily_revenue" in svg


def test_lineage_keeps_twelve_tables_a_side_and_says_how_many_it_left_out() -> None:
    ups = [f"main.bronze.t{k}" for k in range(15)]
    data = lineage.animation("main.silver.orders", ups, [], "2026-11-01")
    assert len(data["tad"]["nodes"]) == 13
    assert data["meta"]["description"].endswith("3 more tables are left out.")
    assert data["steps"][0]["caption"] == "orders is built from the tables on its left."
    assert [g["label"] for g in data["tad"]["groups"]] == ["main.bronze", "main.silver"]
    assert {e["id"] for e in data["tad"]["edges"]} == {f"e{k}" for k in range(1, 13)}
