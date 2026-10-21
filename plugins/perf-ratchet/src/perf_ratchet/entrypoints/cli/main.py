"""`python -m perf_ratchet <command>`: measure journeys, ratchet benchmarks, log changes, report.

Commands print at most 15 lines. Outputs go to files in the data folder.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, TextIO

from perf_ratchet.config.settings import settings_from
from perf_ratchet.connectors.bench.runner import Executor, execute, run_benchmark
from perf_ratchet.connectors.files.store import (
    DataFolder,
    read_changes,
    read_json,
    write_changes,
    write_json,
    write_text,
)
from perf_ratchet.core.budget import DEFAULT_CAP, estimate_budget
from perf_ratchet.core.dashboard import render_document, render_page
from perf_ratchet.core.digest import render_digest
from perf_ratchet.core.model import ROLLOUT_STAGES, BenchRun, Change, Project, Window
from perf_ratchet.core.numbers import pct, speedup
from perf_ratchet.core.ports import SeriesSource
from perf_ratchet.core.project import parse_project, with_ceilings
from perf_ratchet.core.ratchet import judge, tighten
from perf_ratchet.core.records import (
    change_from,
    change_to,
    merge,
    next_change_id,
    parse_bench_import,
    parse_import,
)
from perf_ratchet.core.report import build_metrics
from perf_ratchet.core.writeup import fill, sources_section

SourceFactory = Callable[[str, Project, DataFolder], SeriesSource]
EXIT_OK, EXIT_ERROR, EXIT_FLAGGED = 0, 1, 2
MAX_OUTPUT_LINES = 15
PACKAGE_ROOT = Path(__file__).resolve().parents[2]
PLUGIN_ROOT = PACKAGE_ROOT.parents[1]
OUTLINE = PACKAGE_ROOT / "prompts" / "writeup-outline.md"
WRITER_INSTRUCTIONS = PLUGIN_ROOT / "agents" / "perf-writer.md"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="perf-ratchet", description=__doc__)
    parser.add_argument("--config", type=Path, help="project file (default perf/ratchet.json)")
    parser.add_argument(
        "--data", type=Path, help="data folder (default ~/perf-ratchet-runs/<project>)"
    )
    commands = parser.add_subparsers(dest="command", required=True)

    init = commands.add_parser("init", help="write a starter project file")
    init.add_argument("--project", default="my-app", help="project name")
    init.add_argument("--force", action="store_true", help="overwrite an existing project file")

    measure = commands.add_parser("measure", help="fetch daily values for each journey")
    measure.add_argument("--days", type=int, default=28, help="days to fetch, ending yesterday")
    measure.add_argument("--since", type=date.fromisoformat)
    measure.add_argument("--until", type=date.fromisoformat)
    measure.add_argument("--journey", action="append", default=[], help="only this journey")

    imported = commands.add_parser("import", help="add daily values from JSON or CSV files")
    imported.add_argument("files", nargs="+", type=Path)
    imported.add_argument("--journey", help="journey for files that do not name one")

    for name, text in (
        ("bench", "run benchmarks and record the results"),
        ("guard", "fail when a benchmark is over its ceiling (CI)"),
        ("tighten", "lower ceilings to the latest results; never raise them"),
    ):
        command = commands.add_parser(name, help=text)
        command.add_argument("--benchmark", action="append", default=[], help="only this benchmark")
        command.add_argument("--repeat", type=int, help="override the runs per benchmark")
        command.add_argument(
            "--values", type=Path, help="JSON {benchmark: number} instead of running"
        )
        command.add_argument("--commit", default="", help="commit the results belong to")
        command.add_argument("--day", type=date.fromisoformat, help="day to record (default today)")
        if name == "guard":
            command.add_argument(
                "--strict", action="store_true", help="treat noisy runs as failures"
            )
        if name == "tighten":
            command.add_argument("--dry-run", action="store_true", help="print, do not write")

    log = commands.add_parser("log", help="add or update a change in perf/changes.jsonl")
    log.add_argument("--id", help="update this change instead of adding one")
    log.add_argument("--title")
    log.add_argument("--journey", action="append", default=[])
    log.add_argument("--shipped", type=date.fromisoformat, help="day it reached users, YYYY-MM-DD")
    log.add_argument("--pr", help="pull request link")
    log.add_argument("--flag", help="feature flag name")
    log.add_argument("--stage", choices=ROLLOUT_STAGES)
    log.add_argument("--flag-removed", action="store_true")
    log.add_argument("--benchmark", help="proxy benchmark the change was built against")
    log.add_argument("--before", type=float, help="proxy value before the change")
    log.add_argument("--after", type=float, help="proxy value after the change")
    log.add_argument("--notes")

    report = commands.add_parser("report", help="write metrics, digest and dashboard")
    report.add_argument("--max-tokens", type=int, default=DEFAULT_CAP)

    commands.add_parser("writeup", help="fill writeup.src.md tokens into writeup.md and re-render")
    return parser


class Context:
    def __init__(self, args: argparse.Namespace, env: Mapping[str, str], today: date) -> None:
        settings = settings_from(env)
        self.args = args
        self.today = today
        self.config: Path = args.config or settings.config
        self.settings = settings
        self._raw: dict[str, Any] | None = None
        self._project: Project | None = None
        self._data: DataFolder | None = None

    @property
    def raw(self) -> dict[str, Any]:
        if self._raw is None:
            loaded = read_json(self.config)
            if not isinstance(loaded, dict):
                raise ValueError(f"{self.config} must hold a JSON object")
            self._raw = loaded
        return self._raw

    @property
    def project(self) -> Project:
        if self._project is None:
            self._project = parse_project(self.raw)
        return self._project

    @property
    def data(self) -> DataFolder:
        if self._data is None:
            root = self.args.data or self.settings.runs_root / self.project.name
            self._data = DataFolder(root)
        return self._data

    @property
    def changes_path(self) -> Path:
        return self.config.parent / "changes.jsonl"


def cmd_init(ctx: Context, out: TextIO) -> int:
    if ctx.config.exists() and not ctx.args.force:
        raise ValueError(f"{ctx.config} exists; pass --force to overwrite")
    write_json(ctx.config, starter_project(ctx.args.project))
    if not ctx.changes_path.exists():
        write_text(ctx.changes_path, "")
    _say(
        out,
        [
            f"wrote {ctx.config} and {ctx.changes_path}",
            "next: edit the journeys (source queries, targets, weights) and the baseline window",
            "then: measure (needs DD_API_KEY and DD_APP_KEY) or import files gathered elsewhere",
        ],
    )
    return EXIT_OK


def starter_project(name: str) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "project": name,
        "percentile": "p75",
        "window_days": 7,
        "impact_days": 7,
        "regression_threshold_pct": 5,
        "sources": {"datadog": {"site": "datadoghq.com"}},
        "journeys": [
            {
                "id": "page-load",
                "name": "Page load to interactive",
                "unit": "ms",
                "direction": "lower",
                "target": 1000,
                "weight": 3,
                "source": {
                    "kind": "datadog-rum",
                    "query": "@type:view @application.name:web env:prod",
                    "measure": "@view.loading_time",
                    "aggregation": "pc75",
                    "scale": 1e-6,
                },
            },
            {
                "id": "api-latency",
                "name": "Main API request",
                "unit": "ms",
                "direction": "lower",
                "target": 250,
                "weight": 1,
                "source": {
                    "kind": "datadog-metric",
                    "query": "p75:trace.http.request{service:web,env:prod}",
                    "scale": 1000,
                },
            },
        ],
        "benchmarks": [],
    }


def measure_window(args: argparse.Namespace, today: date) -> Window:
    if (args.since is None) != (args.until is None):
        raise ValueError("--since and --until go together")
    if args.since is not None:
        if args.until < args.since:
            raise ValueError("--until is before --since")
        return Window(args.since, args.until)
    if not 1 <= args.days <= 400:
        raise ValueError("--days must be from 1 to 400")
    until = today - timedelta(days=1)
    return Window(until - timedelta(days=args.days - 1), until)


def cmd_measure(ctx: Context, make_source: SourceFactory, out: TextIO) -> int:
    project = ctx.project
    window = measure_window(ctx.args, ctx.today)
    wanted = set(ctx.args.journey) or {j.id for j in project.journeys}
    for journey_id in wanted:
        project.journey(journey_id)
    history = ctx.data.history()
    lines = [f"data folder: {ctx.data.root}", f"window: {window.since} to {window.until}"]
    warnings: list[str] = []
    sources: dict[str, SeriesSource] = {}
    try:
        for journey in project.journeys:
            if journey.id not in wanted:
                continue
            if journey.source.kind == "file":
                lines.append(f"{journey.id}: file source, skipped (use import)")
                continue
            source = sources.get(journey.source.kind) or make_source(
                journey.source.kind, project, ctx.data
            )
            sources[journey.source.kind] = source
            series = source.fetch(journey, window)
            written = merge(history, series)
            warnings.extend(series.warnings)
            lines.append(f"{journey.id}: {written} days")
    finally:
        ctx.data.save_history(history)  # keep journeys fetched before a later one failed
    lines += [f"warning: {w}" for w in warnings]
    _say(out, [*lines, "next: report"])
    return EXIT_OK


def cmd_import(ctx: Context, out: TextIO) -> int:
    project = ctx.project
    history = ctx.data.history()
    lines = [f"data folder: {ctx.data.root}"]
    for path in ctx.args.files:
        text = path.read_text(encoding="utf-8")
        runs = parse_bench_import(text, path.name)
        if runs is not None:
            for run in runs:
                project.benchmark(run.benchmark)
            ctx.data.add_bench_runs(runs)
            lines.append(f"{path.name}: {len(runs)} benchmark runs")
            continue
        for series in parse_import(text, path.name, ctx.args.journey):
            project.journey(series.journey)
            written = merge(history, series)
            lines.append(f"{path.name}: {series.journey} {written} days")
    ctx.data.save_history(history)
    _say(out, [*lines, "next: report"])
    return EXIT_OK


def _bench_runs(ctx: Context, executor: Executor) -> list[tuple[Any, BenchRun]]:
    project = ctx.project
    chosen = [project.benchmark(b) for b in ctx.args.benchmark] or list(project.benchmarks)
    if not chosen:
        raise ValueError("the project file has no benchmarks")
    day = ctx.args.day or ctx.today
    if ctx.args.values is not None:
        values = read_json(ctx.args.values)
        if not isinstance(values, dict):
            raise ValueError("--values must hold a JSON object of benchmark id to number")
        runs = []
        for benchmark in chosen:
            if benchmark.id not in values:
                raise ValueError(f"--values has no number for {benchmark.id}")
            value = float(values[benchmark.id])
            run = BenchRun(benchmark.id, day, (value,), value, 0.0, ctx.args.commit)
            runs.append((benchmark, run))
        return runs
    cwd = Path.cwd()
    return [
        (b, run_benchmark(b, day, cwd, ctx.args.commit, executor, ctx.args.repeat)) for b in chosen
    ]


def cmd_bench(ctx: Context, executor: Executor, out: TextIO) -> int:
    pairs = _bench_runs(ctx, executor)
    ctx.data.add_bench_runs([run for _, run in pairs])
    lines = [judge(b, run).line() for b, run in pairs]
    _say(out, [*lines, f"recorded in {ctx.data.bench_path}"])
    return EXIT_OK


def cmd_guard(ctx: Context, executor: Executor, out: TextIO) -> int:
    verdicts = [judge(b, run) for b, run in _bench_runs(ctx, executor)]
    failed = [
        v for v in verdicts if v.outcome == "fail" or (ctx.args.strict and v.outcome == "noisy")
    ]
    lines = [v.line() for v in verdicts]
    if failed:
        lines.append(
            f"FAILED: {len(failed)} over ceiling. Make the change cheaper, or explain the cost "
            "in the PR and raise the ceiling by hand in the project file."
        )
    else:
        lines.append(f"passed: {len(verdicts)} benchmarks within their ceilings")
    _say(out, lines)
    return EXIT_FLAGGED if failed else EXIT_OK


def cmd_tighten(ctx: Context, executor: Executor, out: TextIO) -> int:
    lines: list[str] = []
    updates: dict[str, tuple[float, float]] = {}
    for benchmark, run in _bench_runs(ctx, executor):
        result = tighten(benchmark, run)
        if result is None:
            lines.append(f"{benchmark.id}: run too noisy (cv {run.cv_pct:.2f}%); ceiling kept")
            continue
        lines.append(result.line())
        if result.moved:
            updates[benchmark.id] = (result.new, result.original)
    if updates and not ctx.args.dry_run:
        write_json(ctx.config, with_ceilings(ctx.raw, updates))
        lines.append(f"wrote {len(updates)} ceilings to {ctx.config}")
    elif updates:
        lines.append(f"dry run: {len(updates)} ceilings would move")
    _say(out, lines)
    return EXIT_OK


def cmd_log(ctx: Context, out: TextIO) -> int:
    args = ctx.args
    project = ctx.project
    for journey_id in args.journey:
        project.journey(journey_id)
    if args.benchmark:
        project.benchmark(args.benchmark)
    changes = read_changes(ctx.changes_path)
    if args.id:
        index = next((i for i, c in enumerate(changes) if c.id == args.id), None)
        if index is None:
            raise ValueError(f"no change {args.id} in {ctx.changes_path}")
        change = _updated(changes[index], args, ctx.today)
        changes[index] = change
        verb = "updated"
    else:
        if not args.title:
            raise ValueError("a new change needs --title")
        change = _updated(
            Change(id=next_change_id(changes), title=args.title, journeys=[]), args, ctx.today
        )
        changes.append(change)
        verb = "added"
    write_changes(ctx.changes_path, changes)
    _say(out, [f"{verb} {change.id}: {change.title} [{change.stage}] in {ctx.changes_path}"])
    return EXIT_OK


def _updated(change: Change, args: argparse.Namespace, today: date) -> Change:
    """Apply the flags that were given; reaching 100% without a ship day ships it today."""
    fields: dict[str, Any] = {}
    if args.title:
        fields["title"] = args.title
    if args.journey:
        fields["journeys"] = sorted(set(change.journeys) | set(args.journey))
    for name in ("shipped", "pr", "flag", "stage", "benchmark", "notes"):
        value = getattr(args, name)
        if value is not None:
            fields[name] = value
    if args.flag_removed:
        fields["flag_removed"] = True
    if args.before is not None:
        fields["proxy_before"] = args.before
    if args.after is not None:
        fields["proxy_after"] = args.after
    if args.stage == "100%" and change.shipped is None and args.shipped is None:
        fields["shipped"] = today
    candidate = replace(change, **fields)
    return change_from(change_to(candidate))


def cmd_report(ctx: Context, out: TextIO, max_tokens: int | None = None) -> int:
    project = ctx.project
    metrics = build_metrics(
        project,
        ctx.data.history(),
        read_changes(ctx.changes_path),
        ctx.data.bench_runs(),
        datetime.now(UTC),
    )
    writeup_path = ctx.data.path("writeup.md")
    writeup = writeup_path.read_text(encoding="utf-8") if writeup_path.is_file() else None
    digest = render_digest(metrics)
    budget = estimate_budget(
        len(digest.encode("utf-8")), _instructions_bytes(), max_tokens or DEFAULT_CAP
    )
    write_json(ctx.data.path("metrics.json"), metrics)
    write_text(ctx.data.path("digest.md"), digest)
    write_json(ctx.data.path("budget.json"), budget)
    write_text(ctx.data.path("dashboard.html"), render_document(metrics, writeup))
    write_text(ctx.data.path("artifact.html"), render_page(metrics, writeup))
    _say(out, summary_lines(ctx.data.root, metrics, budget, writeup is not None))
    return EXIT_OK if budget["within_cap"] else EXIT_FLAGGED


def summary_lines(
    folder: Path, metrics: dict[str, Any], budget: dict[str, Any], has_writeup: bool
) -> list[str]:
    h = metrics["headline"]
    lines = [
        f"data folder: {folder}",
        f"data through: {metrics['as_of'] or 'no data yet'}",
        f"overall speedup: {speedup(h.get('geomean_speedup'))} over {h['journeys_measured']} "
        f"journeys; "
        f"at target {h['journeys_at_target']}/{h['journeys_with_target']}; "
        f"regressed {h['journeys_regressed']}",
        f"changes: {h['changes']} logged, {h['changes_shipped']} shipped, "
        f"{h['changes_improved']} with a measured win; flags open {h['flags_open']}",
        f"guardrails: {h['guardrails']}, median ceiling cut "
        f"{pct(h.get('median_ceiling_reduction_pct'), False)}",
    ]
    for journey_id, j in metrics["journeys"].items():
        if j.get("regressed"):
            lines.append(f"REGRESSION {journey_id}: {pct(j['vs_previous_pct'])} vs previous window")
    for row in metrics["priorities"][:3]:
        lines.append(
            f"next: {row['journey']} is {pct(row['gap_to_target_pct'], False)} over target"
        )
    lines.append(
        f"model token estimate: {budget['estimated_tokens']} of cap {budget['cap']} "
        f"({'within cap' if budget['within_cap'] else 'OVER CAP'})"
    )
    files = "metrics.json, digest.md, dashboard.html, artifact.html, budget.json"
    lines.append(f"files: {files}{' (with write-up)' if has_writeup else ''}")
    return lines


def cmd_writeup(ctx: Context, out: TextIO) -> int:
    source_path = ctx.data.path("writeup.src.md")
    if not source_path.is_file():
        raise ValueError(f"{source_path} does not exist; the writer writes it first")
    metrics_path = ctx.data.path("metrics.json")
    metrics = read_json(metrics_path)
    filled = fill(source_path.read_text(encoding="utf-8"), metrics)
    write_text(ctx.data.path("writeup.md"), filled.text.rstrip() + "\n" + sources_section(filled))
    lines = [f"wrote {ctx.data.path('writeup.md')} with {len(filled.used)} sourced numbers"]
    if filled.unknown:
        lines.append(f"unknown keys: {', '.join(sorted(set(filled.unknown)))[:400]}")
    if filled.bare:
        lines.append(f"numbers typed by hand: {', '.join(filled.bare[:20])}")
    write_text(
        ctx.data.path("dashboard.html"),
        render_document(metrics, _read(ctx.data.path("writeup.md"))),
    )
    write_text(
        ctx.data.path("artifact.html"), render_page(metrics, _read(ctx.data.path("writeup.md")))
    )
    lines.append("dashboard re-rendered with the write-up")
    _say(out, lines)
    return EXIT_FLAGGED if filled.unknown or filled.bare else EXIT_OK


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _instructions_bytes() -> int | None:
    sizes = [p.stat().st_size for p in (OUTLINE, WRITER_INSTRUCTIONS) if p.is_file()]
    return sum(sizes) if len(sizes) == 2 else None


def _say(out: TextIO, lines: list[str]) -> None:
    for line in lines[:MAX_OUTPUT_LINES]:
        out.write(line + "\n")
    if len(lines) > MAX_OUTPUT_LINES:
        out.write(f"... {len(lines) - MAX_OUTPUT_LINES} more lines in the data folder files\n")


def run(
    argv: Sequence[str] | None,
    make_source: SourceFactory,
    env: Mapping[str, str],
    today: date | None = None,
    out: TextIO | None = None,
    err: TextIO | None = None,
    executor: Executor = execute,
) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    logging.basicConfig(stream=err, level=logging.INFO, format="%(levelname)s %(message)s")
    args = build_parser().parse_args(argv)
    ctx = Context(args, env, today or datetime.now(UTC).date())
    commands: dict[str, Callable[[], int]] = {
        "init": lambda: cmd_init(ctx, out),
        "measure": lambda: cmd_measure(ctx, make_source, out),
        "import": lambda: cmd_import(ctx, out),
        "bench": lambda: cmd_bench(ctx, executor, out),
        "guard": lambda: cmd_guard(ctx, executor, out),
        "tighten": lambda: cmd_tighten(ctx, executor, out),
        "log": lambda: cmd_log(ctx, out),
        "report": lambda: cmd_report(ctx, out, args.max_tokens),
        "writeup": lambda: cmd_writeup(ctx, out),
    }
    try:
        return commands[args.command]()
    except (ValueError, OSError, RuntimeError, KeyError) as error:
        err.write(f"error: {error}\n")
        return EXIT_ERROR
