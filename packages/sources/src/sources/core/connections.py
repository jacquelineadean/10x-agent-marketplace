"""Named connections: where a system lives and which environment variables hold its keys.

The file holds hosts and variable names, never a secret. Every `env` value must look like
a variable name, so a pasted token fails the check; messages never repeat the value.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from sources.core.systems import BY_ID

SCHEMA_VERSION = 1
NAME = re.compile(r"^[a-z][a-z0-9-]{0,31}$")
VARIABLE = re.compile(r"^[A-Z][A-Z0-9_]{1,63}$")
ROLE = re.compile(r"^[a-z][a-z_]{0,31}$")
HOST = re.compile(r"^(https://)?[A-Za-z0-9.-]{1,253}(:[0-9]{1,5})?$")
DATABASE = re.compile(r"^[A-Za-z0-9_.$-]{1,128}$")
PATH = re.compile(r"^/[A-Za-z0-9._~/-]{0,255}$")
FIELDS = ("system", "host", "database", "path", "env")


class ConnectionsError(ValueError):
    """A connections file or entry that cannot be used, with what to change."""


@dataclass(frozen=True)
class Connection:
    """One named place to read from, such as the `warehouse` Postgres database."""

    name: str
    system: str
    host: str
    database: str = ""
    path: str = ""
    env: Mapping[str, str] = field(default_factory=dict)

    def as_json(self) -> dict[str, Any]:
        out: dict[str, Any] = {"system": self.system, "host": self.host}
        if self.database:
            out["database"] = self.database
        if self.path:
            out["path"] = self.path
        if self.env:
            out["env"] = dict(self.env)
        return out


def connection(name: str, entry: Any) -> Connection:
    """Check one entry; raises ConnectionsError naming the field to fix."""
    if not NAME.match(name):
        raise ConnectionsError(f"connection name {name!r} must be lowercase letters, digits, -")
    if not isinstance(entry, Mapping):
        raise ConnectionsError(f"connection {name} must be an object")
    for key in entry:
        if key not in FIELDS:
            raise ConnectionsError(
                f"connection {name}: field {key!r} is unknown; use {', '.join(FIELDS)}. "
                "Keys stay in environment variables, named under env"
            )
    system = str(entry.get("system", ""))
    if system not in BY_ID:
        raise ConnectionsError(f"connection {name}: system must be one of {', '.join(BY_ID)}")
    host = str(entry.get("host", ""))
    if not HOST.match(host):
        raise ConnectionsError(f"connection {name}: host must be a host name or https:// URL")
    database = str(entry.get("database", ""))
    if database and not DATABASE.match(database):
        raise ConnectionsError(f"connection {name}: database must be a plain name")
    path = str(entry.get("path", ""))
    if path and not PATH.match(path):
        raise ConnectionsError(f"connection {name}: path must start with / and hold no query")
    env = entry.get("env", {})
    if not isinstance(env, Mapping):
        raise ConnectionsError(f"connection {name}: env must map a role to a variable name")
    for role, variable in env.items():
        if not ROLE.match(str(role)):
            raise ConnectionsError(f"connection {name}: env role {role!r} must be lowercase")
        if not isinstance(variable, str) or not VARIABLE.match(variable):
            raise ConnectionsError(
                f"connection {name}: env.{role} must name an environment variable "
                "(capital letters, digits, _), never hold the key itself"
            )
    return Connection(name, system, host, database, path, {str(k): v for k, v in env.items()})


def parse(data: Any) -> dict[str, Connection]:
    """Every connection in a connections file."""
    if not isinstance(data, Mapping) or not isinstance(data.get("connections", {}), Mapping):
        raise ConnectionsError("the connections file must hold {'connections': {name: entry}}")
    return {str(k): connection(str(k), v) for k, v in data.get("connections", {}).items()}


def to_json(found: Mapping[str, Connection]) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "connections": {name: c.as_json() for name, c in sorted(found.items())},
    }
