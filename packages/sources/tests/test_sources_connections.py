"""Named connections hold hosts and variable names, never a key."""

from __future__ import annotations

import pytest
from sources.core.connections import ConnectionsError, connection, parse, to_json


def test_a_connection_round_trips() -> None:
    entry = {
        "system": "postgres",
        "host": "db.internal:5432",
        "database": "analytics",
        "env": {"user": "PGUSER", "password": "PGPASSWORD"},
    }
    found = parse({"connections": {"warehouse": entry}})
    assert to_json(found) == {"schema_version": 1, "connections": {"warehouse": entry}}


@pytest.mark.parametrize(
    ("entry", "message"),
    [
        ({"system": "mysql", "host": "db"}, "system must be one of"),
        ({"system": "postgres", "host": "db; rm -rf /"}, "host must be"),
        ({"system": "postgres", "host": "db", "password": "hunter2"}, "field 'password'"),
        ({"system": "postgres", "host": "db", "env": {"password": "hunter2"}}, "never hold"),
        ({"system": "databricks", "host": "https://x.cloud", "path": "/sql?x=1"}, "path"),
    ],
)
def test_bad_connections_say_what_to_change_without_echoing_values(
    entry: dict[str, object], message: str
) -> None:
    with pytest.raises(ConnectionsError, match=message) as caught:
        connection("warehouse", entry)
    assert "hunter2" not in str(caught.value)


def test_connection_names_are_plain() -> None:
    with pytest.raises(ConnectionsError, match="lowercase"):
        connection("Prod DB", {"system": "postgres", "host": "db"})
