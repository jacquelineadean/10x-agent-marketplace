"""The `sources` command line: detect, gather, check, digest, connection and agent."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from pathlib import Path
from typing import Any

from sources.config import settings
from sources.connectors.files import store
from sources.connectors.system import probe
from sources.core import agent, connections, contract, detect, digest, picker, systems
from sources.entrypoints.cli import gather


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sources", description="Read-only access to company systems.")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("detect", help="which systems this machine and session can reach")
    d.add_argument(
        "--connectors",
        default="",
        help="comma-separated MCP server names from the session's tool list",
    )
    shape = d.add_mutually_exclusive_group()
    shape.add_argument("--json", action="store_true", help="one object per system")
    shape.add_argument("--picker", action="store_true", help="AskUserQuestion questions")
    g = sub.add_parser("gather", help="run the script-lane queries, then write digest.md")
    g.add_argument("run", type=Path, help="the run folder")
    g.add_argument("--only", action="append", default=[], metavar="PATH", help="one entry")
    g.add_argument(
        "--roll", action="store_true", help="move each window to the last complete period"
    )
    g.add_argument("--until", type=date.fromisoformat, help="the as-of date (default today)")
    for name, text in (
        ("check", "check facts.json against queries.json"),
        ("digest", "check the run folder, then write digest.md"),
    ):
        c = sub.add_parser(name, help=text)
        c.add_argument("run", type=Path, help="the run folder")
    conn = sub.add_parser("connection", help="named connections: hosts and variable names")
    csub = conn.add_subparsers(dest="action", required=True)
    csub.add_parser("list", help="show the named connections")
    add = csub.add_parser("add", help="add or replace a named connection")
    add.add_argument("name")
    add.add_argument("--system", required=True, choices=list(systems.BY_ID))
    add.add_argument("--host", required=True, help="host name or https:// URL")
    add.add_argument("--database", default="")
    add.add_argument("--path", default="", help="an HTTP path, such as a SQL warehouse's")
    add.add_argument(
        "--env",
        action="append",
        default=[],
        metavar="ROLE=VARIABLE",
        help="an environment variable that holds a key, such as password=PGPASSWORD",
    )
    rm = csub.add_parser("remove", help="remove a named connection")
    rm.add_argument("name")
    a = sub.add_parser("agent", help="write the user-level database agent, sources-db")
    a.add_argument("--connection", action="append", default=[], help="a database connection")
    a.add_argument("--force", action="store_true", help="replace an existing agent file")
    return p


def _connections() -> dict[str, connections.Connection]:
    return connections.parse(store.read_json_or(settings.connections_path(), {}))


def _detect(args: argparse.Namespace) -> int:
    agent_file = settings.claude_dir() / "agents" / agent.FILE
    served = agent.systems_in(store.read_text(agent_file)) if agent_file.is_file() else set()
    found = detect.detect(
        settings.present(systems.key_names()),
        probe.installed(systems.program_names()),
        args.connectors.split(","),
        _connections(),
        served,
    )
    if args.json:
        print(json.dumps([s.as_json() for s in found], indent=1))
    elif args.picker:
        print(json.dumps(picker.questions(found), indent=1))
    else:
        for status in found:
            print(f"{status.system.label}: {status.text}")
    return 0


def _read(run: Path) -> tuple[Any, Any]:
    """A run's facts and queries, read once for both the check and the digest."""
    return store.read_json(run / "facts.json"), store.read_json(run / "queries.json")


def _check(facts: Any, queries: Any) -> contract.Report:
    report = contract.check(facts, queries, date.today())
    for line in report.errors:
        print(f"error: {line}", file=sys.stderr)
    for line in report.warnings:
        print(f"warning: {line}", file=sys.stderr)
    return report


def _digest(run: Path) -> int:
    facts, queries = _read(run)
    if _check(facts, queries).errors:
        return 1
    text = digest.render(facts, queries, date.today())
    store.write_text(run / "digest.md", text)
    print(f"wrote {run / 'digest.md'} ({len(text.encode('utf-8'))} bytes)")
    return 0


def _connection(args: argparse.Namespace) -> int:
    path = settings.connections_path()
    found = _connections()
    if args.action == "list":
        for name, c in sorted(found.items()):
            print(f"{name}: {c.system} at {c.host}" + (f"/{c.database}" if c.database else ""))
        print(f"({len(found)} in {path})")
        return 0
    if args.action == "remove":
        if args.name not in found:
            print(f"error: no connection {args.name} in {path}", file=sys.stderr)
            return 1
        del found[args.name]
    else:
        env = {}
        for item in args.env:
            role, _, variable = item.partition("=")
            env[role.strip()] = variable.strip()
        entry = {
            "system": args.system,
            "host": args.host,
            "database": args.database,
            "path": args.path,
            "env": env,
        }
        found[args.name] = connections.connection(args.name, {k: v for k, v in entry.items() if v})
    store.write_json(path, connections.to_json(found))
    print(f"wrote {path} ({len(found)} connections)")
    return 0


def _agent(args: argparse.Namespace) -> int:
    path = settings.claude_dir() / "agents" / agent.FILE
    if path.exists() and not args.force:
        print(f"error: {path} exists; pass --force to replace it", file=sys.stderr)
        return 1
    found = _connections()
    unknown = [n for n in args.connection if n not in found]
    if unknown:
        where = settings.connections_path()
        print(f"error: no connection {', '.join(unknown)} in {where}", file=sys.stderr)
        return 1
    chosen = [found[n] for n in args.connection] or [
        c for c in found.values() if c.system in agent.SERVERS
    ]
    text = agent.render(chosen)
    store.write_text(path, text)
    print(f"wrote {path}; restart Claude Code to load it")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "detect":
            return _detect(args)
        if args.command == "gather":
            return gather.run(args.run, args.only, args.roll, args.until)
        if args.command == "check":
            return 1 if _check(*_read(args.run)).errors else 0
        if args.command == "digest":
            return _digest(args.run)
        if args.command == "connection":
            return _connection(args)
        return _agent(args)
    except (store.StoreError, connections.ConnectionsError, agent.AgentError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
