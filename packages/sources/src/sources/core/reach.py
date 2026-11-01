"""Where a collector reads and with which keys: a named connection or the system's defaults.

A queries entry's `connection` names a connection in `connections.json`, or is the
system's id for the default variables below. A named connection gives the host, database
and path, and maps roles to variables; a role it leaves out falls back to the default.
Values live only in the `Reach`; messages name variables, never what they hold.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

from sources.core.connections import Connection

ROLES: dict[str, dict[str, tuple[str, ...]]] = {
    "github": {"token": ("GITHUB_TOKEN", "GH_TOKEN")},
    "jira": {"url": ("JIRA_URL",), "email": ("JIRA_EMAIL",), "token": ("JIRA_API_TOKEN",)},
    "confluence": {
        "url": ("CONFLUENCE_URL",),
        "email": ("CONFLUENCE_EMAIL",),
        "token": ("CONFLUENCE_API_TOKEN",),
    },
    "datadog": {
        "api_key": ("DD_API_KEY",),
        "app_key": ("DD_APP_KEY", "DD_APPLICATION_KEY"),
        "site": ("DD_SITE",),
    },
    "pagerduty": {"token": ("PAGERDUTY_TOKEN",)},
    "servicenow": {
        "url": ("SERVICENOW_INSTANCE",),
        "user": ("SERVICENOW_USER",),
        "password": ("SERVICENOW_PASSWORD",),
        "token": ("SERVICENOW_TOKEN",),
    },
    "databricks": {"url": ("DATABRICKS_HOST",), "token": ("DATABRICKS_TOKEN",)},
    "postgres": {"url": ("DATABASE_URL",), "user": ("PGUSER",), "password": ("PGPASSWORD",)},
    "oracle": {"user": ("ORACLE_USER",), "password": ("ORACLE_PASSWORD",), "dsn": ("ORACLE_DSN",)},
}


class ReachError(ValueError):
    """A connection that cannot be used, naming the variable or field to set."""


@dataclass(frozen=True)
class Reach:
    system: str
    name: str
    host: str = ""
    database: str = ""
    path: str = ""
    keys: Mapping[str, str] = field(default_factory=dict, repr=False)
    variables: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def key(self, role: str) -> str:
        return self.keys.get(role, "")

    def need(self, *roles: str) -> list[str]:
        """The values of `roles`; a missing one raises an error naming its variables."""
        missing = [r for r in roles if not self.key(r)]
        if missing:
            names = " and ".join(" or ".join(self.variables.get(r, (r,))) for r in missing)
            raise ReachError(f"{self.system} ({self.name}) needs {names} set")
        return [self.key(r) for r in roles]

    def url(self) -> str:
        """The base URL: the named connection's host, else the `url` key, as https."""
        raw = (self.host or self.key("url")).strip().rstrip("/")
        if not raw:
            names = " or ".join(self.variables.get("url", ("a host",)))
            raise ReachError(f"{self.system} ({self.name}) needs {names} set")
        if raw.startswith("http://"):
            raise ReachError(f"{self.system} ({self.name}) must use https://")
        return raw if raw.startswith("https://") else f"https://{raw}"


def reach(
    system: str, name: str, named: Mapping[str, Connection], environ: Mapping[str, str]
) -> Reach:
    """The Reach for a queries entry's system and connection."""
    defaults = ROLES[system]
    variables = dict(defaults)
    host = database = path = ""
    if name in named:
        connection = named[name]
        if connection.system != system:
            raise ReachError(f"connection {name} reads {connection.system}, not {system}")
        host, database, path = connection.host, connection.database, connection.path
        variables.update({role: (var,) for role, var in connection.env.items()})
    elif name != system:
        raise ReachError(
            f"connection {name} is not in connections.json; name one there "
            f"(sources connection add) or use {system!r} for the default variables"
        )
    keys = {}
    for role, names in variables.items():
        value = next((environ[n].strip() for n in names if environ.get(n, "").strip()), "")
        if value:
            keys[role] = value
    return Reach(system, name, host, database, path, keys, variables)
