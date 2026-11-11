"""Which systems this machine and session can reach, and by which lane.

A system is readable when the session has its MCP connector, the user-level database
agent serves it, or its script collector is ready: a full set of keys or a named
connection, plus the program it runs (psql for Postgres, SQLcl for Oracle). A signed-in
`gh` stands in for GitHub's keys.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from sources.core.connections import Connection
from sources.core.systems import SYSTEMS, System

NOT_SET_UP = "not set up: run /sources:connect"


@dataclass(frozen=True)
class Status:
    """What was found for one system."""

    system: System
    connector: str = ""
    agent: bool = False
    keys: tuple[str, ...] = ()
    connections: tuple[str, ...] = ()
    programs: tuple[str, ...] = ()

    @property
    def collector(self) -> bool:
        """`sources gather` can read it with what this machine has."""
        reach = bool(self.keys or self.connections) or "gh" in self.programs
        return reach and (not self.system.runs or self.system.runs in self.programs)

    @property
    def readable(self) -> bool:
        """The gatherer can read it in this session, through a connector or a collector."""
        return bool(self.connector) or self.agent or self.collector

    @property
    def text(self) -> str:
        """The status as the picker shows it: 'connected through atlassian; psql found'."""
        parts = []
        if self.connector:
            parts.append(f"connected through {self.connector}")
        if self.agent:
            parts.append("sources-db agent")
        if self.keys:
            parts.append(f"{' and '.join(self.keys)} set")
        if self.connections:
            parts.append(f"connection {', '.join(self.connections)}")
        if self.programs:
            parts.append(f"{', '.join(self.programs)} found")
        if not parts:
            return NOT_SET_UP
        if self.collector:
            parts.append("script collector ready")
        elif not self.readable:
            parts.append("no connector in this session")
        return "; ".join(parts)

    def as_json(self) -> dict[str, object]:
        return {
            "id": self.system.id,
            "label": self.system.label,
            "group": self.system.group,
            "readable": self.readable,
            "collector": self.collector,
            "connector": self.connector,
            "agent": self.agent,
            "keys": list(self.keys),
            "connections": list(self.connections),
            "programs": list(self.programs),
            "status": self.text,
        }


def _words(name: str) -> set[str]:
    return set(re.split(r"[^a-z0-9]+", name.lower())) - {""}


def detect(
    present: set[str],
    programs: set[str],
    connectors: Iterable[str],
    connections: Mapping[str, Connection],
    agent_systems: set[str],
) -> list[Status]:
    """Statuses for every system, in picker order.

    `present` holds the environment variable names that are set (never their values);
    `connectors` holds the MCP server names Claude sees in the session's tool list.
    """
    servers = [c.strip() for c in connectors if c.strip()]
    out = []
    for system in SYSTEMS:
        server = next((s for s in servers if _words(s) & set(system.connectors)), "")
        keys = next((group for group in system.keys if set(group) <= present), ())
        named = tuple(sorted(n for n, c in connections.items() if c.system == system.id))
        found = tuple(p for p in system.programs if p in programs)
        out.append(Status(system, server, system.id in agent_systems, tuple(keys), named, found))
    return out
