"""`solutions`: start a solutions run, simulate it into results and a digest, and turn the
decision a reader exports from the page into `decision.md`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from chronicle_engine.connectors.files import store
from chronicle_engine.core.story.facts import FactError
from chronicle_engine.core.story.model import SCHEMA_VERSION, Report, blocks_of
from chronicle_engine.entrypoints.cli import runs

from blueprint.core.solutions import decision, digest, formula, simulate

FILE = "solutions.json"
SOLUTIONS: dict[str, Any] = {
    "question": "State the design question in one sentence.",
    "inputs": [
        {
            "id": "load",
            "label": "Requests per second",
            "unit": "rps",
            "value": 100,
            "min": 10,
            "max": 1000,
            "step": 10,
        }
    ],
    "settings": [
        {"id": "workers", "label": "Workers", "value": 4, "min": 1, "max": 32, "key": "WORKERS"}
    ],
    "scenarios": [
        {"id": "typical", "label": "Typical"},
        {"id": "peak", "label": "Peak", "inputs": {"load": 800}},
    ],
    "measures": [
        {"id": "wait_ms", "label": "Response time", "unit": "ms", "budget": 300, "feel": "wait"}
    ],
    "approaches": [
        {
            "id": "first",
            "label": "First approach",
            "text": "Say what it does and what it costs.",
            "measures": {"wait_ms": "40 + 200 * min(1, load / (workers * 60))"},
        },
        {
            "id": "second",
            "label": "Second approach",
            "text": "Say what it does and what it costs.",
            "measures": {"wait_ms": "90 + 20 * min(1, load / (workers * 200))"},
        },
    ],
}


def parser(sub: Any) -> None:
    p = sub.add_parser("solutions", help="approaches to one design question: new, simulate, decide")
    actions = p.add_subparsers(dest="action", required=True)
    new = actions.add_parser("new", help="start a run folder with a story and a solutions file")
    new.add_argument("folder", type=Path, help="run folder to create, e.g. blueprint-runs/reads")
    new.add_argument("--title", default="", help="the design question's short name")
    sim = actions.add_parser("simulate", help="write the results facts and the digest")
    sim.add_argument("story", type=Path, help="path to story.json")
    dec = actions.add_parser("decide", help="check an exported decision and write decision.md")
    dec.add_argument("story", type=Path, help="path to story.json")
    dec.add_argument("--decision", type=Path, required=True, help="the JSON the page exported")


def run(args: argparse.Namespace) -> int:
    try:
        if args.action == "new":
            return _new(args.folder, args.title)
        if args.action == "simulate":
            return _simulate(args.story)
        return _decide(args.story, args.decision)
    except (store.StoreError, FactError, formula.FormulaError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def _story(title: str) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "layout": "prototype",
        "facts_file": ["facts.json", _results_name(FILE)],
        "meta": {"title": title, "kicker": "", "dek": ""},
        "theme": {"concept": ""},
        "sources": [
            {
                "id": digest.SOURCE,
                "label": "Simulation model",
                "detail": f"Computed from the formulas in {FILE}.",
            }
        ],
        "chapters": [
            {
                "id": "compare",
                "title": "Compare",
                "blocks": [{"type": "solutions", "file": FILE}],
            }
        ],
    }


def _results_name(file: str) -> str:
    return f"{digest.fact_key(file)}-results.json"


def _new(folder: Path, title: str) -> int:
    story = folder / "story.json"
    if story.exists():
        print(f"error: {story} exists; pick another folder", file=sys.stderr)
        return 1
    name = title or folder.name.replace("-", " ").title()
    store.write_json(story, _story(name))
    store.write_json(folder / "facts.json", {"derive": {}})
    store.write_json(folder / FILE, {"title": name, **SOLUTIONS})
    ignored = runs.ignore(folder)
    print(f"wrote {story}, {folder / FILE} and {folder / 'facts.json'}")
    if ignored:
        print(f"added {ignored} to .gitignore")
    code = _simulate(story)
    print(f"next: write {FILE}, then solutions simulate, check and build")
    return code


def _load(story_path: Path) -> tuple[simulate.Run, Path] | None:
    """The story's one solutions file, read and simulated; errors go to stderr."""
    story = store.read_json(story_path)
    block = next((b for _, b in blocks_of(story, "solutions")), None)
    if block is None or not block.get("file"):
        print(f"error: {story_path} has no solutions block with a file", file=sys.stderr)
        return None
    path = story_path.parent / str(block["file"])
    # The stored results are this command's own output: the model never reads them, and
    # a run whose results file is gone must still simulate.
    listed = story.get("facts_file") or "facts.json"
    names = [listed] if isinstance(listed, str) else list(listed)
    kept = [name for name in names if name != _results_name(path.name)]
    facts = runs.load_facts(
        story_path, {**story, "facts_file": kept or "facts.json"}, None, default_required=True
    )
    report = Report()
    found = simulate.run(store.read_text(path), facts, report)
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    return (found, path) if found else None


def _simulate(story_path: Path) -> int:
    loaded = _load(story_path)
    if loaded is None:
        return 1
    found, path = loaded
    key = digest.fact_key(path.name)
    results = path.with_name(_results_name(path.name))
    summary = path.with_name(f"{key}-digest.md")
    store.write_json(results, {key: digest.facts(found)})
    store.write_text(summary, digest.digest(found, key))
    spec = found.spec
    print(
        f"wrote {results} and {summary}: {len(spec['approaches'])} approaches, "
        f"{len(spec['scenarios'])} scenarios, {len(spec['measures'])} measures, "
        f"{len(digest.misses(spec, found.results))} budget miss(es)"
    )
    print(f"read {summary}; cite numbers as {{{{{key}.<scenario>.<approach>.<measure>}}}}")
    return 0


def _decide(story_path: Path, decision_path: Path) -> int:
    loaded = _load(story_path)
    if loaded is None:
        return 1
    found, _ = loaded
    report = Report()
    chosen = decision.read(found.spec, store.read_json(decision_path), report)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    if chosen is None:
        print("the decision does not fit the solutions file; export it again", file=sys.stderr)
        return 1
    out = decision_path.with_suffix(".md")
    store.write_text(out, decision.brief(found.spec, chosen))
    print(f"wrote {out}: {chosen['chosen']['label']}; read it, then implement from it")
    return 0
