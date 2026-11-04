"""`python -m tokenwise <command>`: audit sessions, apply or undo fixes, write handoffs, hooks.

Commands print at most 15 lines. Outputs go to files in the data folder.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import TextIO

from tokenwise.config.settings import Settings, settings_from
from tokenwise.connectors.files.store import (
    DataFolder,
    Transcript,
    find_transcripts,
    read_json,
    subagent_transcripts,
    write_json,
    write_text,
)
from tokenwise.core.fixes import applicable
from tokenwise.core.model import TIERS, Finding
from tokenwise.core.report import build_metrics, render_digest
from tokenwise.entrypoints.cli.actions import (
    apply_low_risk,
    describe,
    run_audit,
    undo_last,
    write_handoff,
)
from tokenwise.entrypoints.cli.hooks import run_hook

EXIT_OK, EXIT_ERROR = 0, 1
TOP_FINDINGS = 6


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="tokenwise", description=__doc__)
    parser.add_argument("--project", type=Path, default=Path.cwd(), help="project folder")
    commands = parser.add_subparsers(dest="command", required=True)
    audit = commands.add_parser("audit", help="audit recent sessions and write the digest")
    audit.add_argument("--days", type=int, default=14, help="sessions changed in the last N days")
    audit.add_argument("--transcript", type=Path, help="audit one transcript file")
    audit.add_argument("--apply", action="store_true", help="also apply low-risk fixes")
    commands.add_parser("apply", help="apply low-risk fixes from the last audit")
    commands.add_parser("undo", help="revert the last batch of applied fixes")
    handoff = commands.add_parser("handoff", help="write handoff facts for a fresh session")
    handoff.add_argument("--transcript", type=Path, help="default: newest session")
    hook = commands.add_parser("hook", help="run as a Claude Code hook (reads stdin)")
    hook.add_argument("event", choices=("stop", "pre-compact", "bash-result"))
    return parser


def run(
    argv: Sequence[str] | None = None,
    settings: Settings | None = None,
    stdin: TextIO = sys.stdin,
    out: TextIO = sys.stdout,
    now: datetime | None = None,
) -> int:
    logging.basicConfig(level=logging.WARNING, format="tokenwise: %(message)s")
    args = build_parser().parse_args(argv)
    settings = settings or settings_from()
    clock = now or datetime.now().astimezone()
    try:
        if args.command == "hook":
            return run_hook(args.event, json.load(stdin), settings, out, clock)
        project = args.project.resolve()
        data = DataFolder.for_project(settings.runs_root, project)
        if args.command == "audit":
            return _audit(args, project, data, settings, out, clock)
        if args.command == "apply":
            return _apply(project, data, out, clock)
        if args.command == "undo":
            return _undo(project, data, out, clock)
        return _handoff(args, project, data, settings, out, clock)
    except (OSError, ValueError, KeyError) as error:
        print(f"tokenwise: {error}", file=sys.stderr)
        return EXIT_ERROR


def _audit(
    args: argparse.Namespace,
    project: Path,
    data: DataFolder,
    settings: Settings,
    out: TextIO,
    now: datetime,
) -> int:
    if args.transcript:
        path = args.transcript.resolve()
        transcripts = [Transcript(path, path.stem), *subagent_transcripts(path)]
    else:
        since = now - timedelta(days=args.days)
        transcripts = find_transcripts(settings.claude_dir, project, since)
    if not transcripts:
        print(f"No transcripts for {project} in the last {args.days} days.", file=out)
        return EXIT_OK
    result = run_audit(transcripts, project, settings.claude_dir)
    stamp = now.isoformat(timespec="seconds")
    write_json(data.root / "findings.json", [f.to_dict() for f in result.findings])
    applied = apply_low_risk(project, data, result.findings, stamp) if args.apply else []
    metrics = build_metrics(
        project.name, stamp, list(result.usages.values()), result.findings, applied
    )
    write_json(data.root / "metrics.json", metrics)
    write_text(data.root / "digest.md", render_digest(metrics, result.findings))
    tiers = ", ".join(f"{metrics['by_tier'][t]} {t}" for t in TIERS)
    lines = [
        f"{metrics['sessions']} sessions, {metrics['subagent_runs']} subagent runs, "
        f"{metrics['weighted_tokens']:,} weighted tokens.",
        f"{len(result.findings)} findings ({tiers}), "
        f"{metrics['at_stake_tokens']:,} tokens at stake.",
        *(f"{f.tier.upper()} {f.title} (~{f.at_stake:,})" for f in result.findings[:TOP_FINDINGS]),
        *(f"APPLIED {describe(c)}" for c in applied),
        f"{len(applicable(result.findings))} low-risk fixes can be applied with `apply`.",
        f"Digest: {data.root / 'digest.md'}",
    ]
    print("\n".join(lines[:15]), file=out)
    return EXIT_OK


def _apply(project: Path, data: DataFolder, out: TextIO, now: datetime) -> int:
    raw = read_json(data.root / "findings.json", None)
    if raw is None:
        print("No audit yet. Run `tokenwise audit` first.", file=out)
        return EXIT_ERROR
    findings = [Finding.from_dict(f) for f in raw]
    changes = apply_low_risk(project, data, findings, now.isoformat(timespec="seconds"))
    if not changes:
        print("Nothing new to apply.", file=out)
    for change in changes[:14]:
        print(f"APPLIED {describe(change)}", file=out)
    return EXIT_OK


def _undo(project: Path, data: DataFolder, out: TextIO, now: datetime) -> int:
    changes = undo_last(project, data, now.isoformat(timespec="seconds"))
    if not changes:
        print("Nothing to undo.", file=out)
    for change in changes[:14]:
        print(f"REVERTED {describe(change)}", file=out)
    return EXIT_OK


def _handoff(
    args: argparse.Namespace,
    project: Path,
    data: DataFolder,
    settings: Settings,
    out: TextIO,
    now: datetime,
) -> int:
    path = args.transcript
    if path is None:
        every = find_transcripts(settings.claude_dir, project, datetime.fromtimestamp(0, UTC))
        mains = [t for t in every if not t.agent_type]
        if not mains:
            print(f"No transcripts for {project}.", file=out)
            return EXIT_ERROR
        path = max(mains, key=lambda t: t.path.stat().st_mtime).path
    target = write_handoff(path.resolve(), data, now)
    print(f"Handoff: {target}", file=out)
    return EXIT_OK
