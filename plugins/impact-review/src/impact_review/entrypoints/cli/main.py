"""`python -m impact_review collect`: parse flags, run the collector, write the run folder."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import TextIO

from impact_review.config.settings import settings_from
from impact_review.core.budget import DEFAULT_CAP, estimate_budget
from impact_review.core.dashboard import render_dashboard_html, render_dashboard_md
from impact_review.core.digest import render_digest
from impact_review.core.models import Timeframe
from impact_review.core.ports import ActivitySource
from impact_review.core.report import build_metrics
from impact_review.core.scope import DEFAULT_MAX_PEOPLE, Scope, finish_scope, parse_scope
from impact_review.core.timeframe import parse_timeframe

SourceFactory = Callable[[str], ActivitySource]
EXIT_OK, EXIT_ERROR, EXIT_OVER_CAP = 0, 1, 2
MAX_OUTPUT_LINES = 15
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PACKAGE_ROOT.parents[1]
RUBRICS = {
    "individual": PACKAGE_ROOT / "prompts" / "rubric-individual.md",
    "group": PACKAGE_ROOT / "prompts" / "rubric-group.md",
}
WRITER_INSTRUCTIONS = PLUGIN_ROOT / "agents" / "impact-writer.md"


def build_parser(default_host: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="impact_review", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    collect = commands.add_parser("collect", help="collect GitHub activity and write a run folder")
    collect.add_argument(
        "--scope",
        default="me",
        help="whose work: 'me' (default), 'user:LOGIN[,LOGIN]', 'team:ORG/SLUG', 'org:ORG' "
        "or 'enterprise:SLUG'",
    )
    collect.add_argument(
        "--exclude", action="append", default=[], help="leave this login out (repeatable)"
    )
    collect.add_argument(
        "--max-people",
        type=int,
        default=DEFAULT_MAX_PEOPLE,
        help=f"stop when the scope resolves to more people (default {DEFAULT_MAX_PEOPLE})",
    )
    collect.add_argument(
        "--timeframe",
        default="ytd",
        help="'ytd' (default), 'mtd', 'qtd', 'last month', 'last quarter', 'last year', "
        "'all time', '30d', '3m', '1y', '2025', '2026-Q3', '2026-03' or 'A..B'",
    )
    collect.add_argument("--since", type=date.fromisoformat, help="start date, with --until")
    collect.add_argument("--until", type=date.fromisoformat, help="end date, with --since")
    collect.add_argument(
        "--org",
        action="append",
        default=[],
        help="keep repositories owned by this org only (repeatable); team, org and "
        "enterprise scopes default to their own organizations",
    )
    collect.add_argument(
        "--host", default=default_host, help=f"GitHub host (default {default_host})"
    )
    collect.add_argument("--out", type=Path, help="run folder (default ~/impact-review-runs/...)")
    collect.add_argument("--refresh", action="store_true", help="ignore cached API responses")
    collect.add_argument(
        "--repo-share", action="store_true", help="also fetch per-repo contributor statistics"
    )
    collect.add_argument("--max-tokens", type=int, default=DEFAULT_CAP, help="model token cap")
    collect.add_argument(
        "--rubric",
        type=Path,
        help="rubric file (default: the individual rubric for one person, the group rubric "
        "for several)",
    )
    return parser


def resolve_timeframe(
    args: argparse.Namespace, today: date, earliest: date | None = None
) -> Timeframe:
    """`--since/--until` win over `--timeframe`; `earliest` anchors `all time`."""
    if (args.since is None) != (args.until is None):
        raise ValueError("--since and --until go together")
    if args.since is not None:
        return parse_timeframe(f"{args.since}..{args.until}", today)
    return parse_timeframe(args.timeframe, today, earliest)


def run_folder(args: argparse.Namespace, runs_root: Path, slug: str, timeframe: Timeframe) -> Path:
    if args.out is not None:
        out: Path = args.out
        return out
    return runs_root / str(args.host) / slug / f"{timeframe.since}_{timeframe.until}"


def rubric_for(args: argparse.Namespace, scope: Scope) -> Path:
    if args.rubric is not None:
        chosen: Path = args.rubric
        return chosen
    return RUBRICS["individual" if scope.is_individual else "group"]


def _instructions_bytes(rubric: Path) -> int | None:
    sizes = [path.stat().st_size for path in (rubric, WRITER_INSTRUCTIONS) if path.is_file()]
    return sum(sizes) if len(sizes) == 2 else None


def collect(
    args: argparse.Namespace,
    make_source: SourceFactory,
    env: Mapping[str, str],
    today: date,
    out: TextIO,
) -> int:
    settings = settings_from(env)
    request = parse_scope(args.scope)
    resolve_timeframe(args, today)  # reject a bad timeframe before any network call
    if args.max_people < 1:
        raise ValueError("--max-people needs a value of at least 1")
    source = make_source(args.host)
    people, scope_orgs = source.resolve(request)
    scope = finish_scope(request, people, scope_orgs, args.exclude, args.max_people)
    created = [person.created_at for person in scope.people if person.created_at]
    timeframe = resolve_timeframe(args, today, min(created) if created else None)
    orgs = [org.lower() for org in args.org] or list(scope.orgs)
    folder = run_folder(args, settings.runs_root, scope.slug, timeframe)
    folder.mkdir(parents=True, exist_ok=True)
    source.enable_cache(folder / "raw", args.refresh)
    activity = source.collect(timeframe, scope, orgs, args.repo_share)
    metrics = build_metrics(scope, timeframe, activity, args.host, datetime.now(UTC), orgs)
    digest = render_digest(metrics)
    rubric = rubric_for(args, scope)
    budget = estimate_budget(
        len(digest.encode("utf-8")), _instructions_bytes(rubric), args.max_tokens
    )
    (folder / "metrics.json").write_text(json.dumps(metrics, indent=1), encoding="utf-8")
    (folder / "digest.md").write_text(digest, encoding="utf-8")
    (folder / "dashboard.md").write_text(render_dashboard_md(metrics), encoding="utf-8")
    (folder / "dashboard.html").write_text(render_dashboard_html(metrics), encoding="utf-8")
    (folder / "budget.json").write_text(json.dumps(budget, indent=1), encoding="utf-8")
    if not rubric.is_file():
        raise ValueError(f"rubric file {rubric} not found")
    if rubric.resolve() != (folder / "rubric.md").resolve():
        (folder / "rubric.md").write_text(rubric.read_text(encoding="utf-8"), encoding="utf-8")
    for line in summary_lines(folder, metrics, budget):
        out.write(line + "\n")
    return EXIT_OK if budget["within_cap"] else EXIT_OVER_CAP


def summary_lines(folder: Path, metrics: dict[str, object], budget: dict[str, object]) -> list[str]:
    """At most 15 lines for the conversation; the digest itself is never printed."""
    v = metrics["volume"]
    assert isinstance(v, dict)  # noqa: S101  metrics is built in core with this shape
    frame, scope = metrics["timeframe"], metrics["scope"]
    assert isinstance(frame, dict) and isinstance(scope, dict)  # noqa: S101  same
    lines = [
        f"run folder: {folder}",
        f"scope: {scope['label']} on {metrics['host']}",
        f"timeframe: {frame['since']} to {frame['until']} ({frame['label']}, {frame['days']} days)",
        f"commits {v['commits']}, PRs opened {v['prs_opened']}, merged {v['prs_merged']}, "
        f"reviews {v['reviews']}, issues {v['issues_opened']}, repos {v['repos_touched']}",
        f"model token estimate: {budget['estimated_tokens']} of cap {budget['cap']} "
        f"({'within cap' if budget['within_cap'] else 'OVER CAP'})",
        "files: metrics.json, digest.md, dashboard.md, dashboard.html, budget.json, rubric.md",
    ]
    warnings = metrics["warnings"]
    assert isinstance(warnings, list)  # noqa: S101  same
    if warnings:
        lines.append(f"warnings: {len(warnings)} (see metrics.json warnings)")
    if not budget["within_cap"]:
        lines.append("over cap: trim the digest, raise --max-tokens, or cancel before writing")
    return lines[:MAX_OUTPUT_LINES]


def run(
    argv: Sequence[str] | None,
    make_source: SourceFactory,
    env: Mapping[str, str],
    today: date | None = None,
    out: TextIO = sys.stdout,
    err: TextIO = sys.stderr,
) -> int:
    logging.basicConfig(stream=err, level=logging.INFO, format="%(levelname)s %(message)s")
    settings = settings_from(env)
    args = build_parser(settings.host).parse_args(argv)
    try:
        return collect(args, make_source, env, today or date.today(), out)
    except (ValueError, OSError, RuntimeError) as error:
        err.write(f"error: {error}\n")
        return EXIT_ERROR
