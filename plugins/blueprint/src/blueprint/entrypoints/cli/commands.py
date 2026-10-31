"""blueprint's commands and its check: `schema` turns a schema export into an `erd` object,
`sources` runs the linked sources command."""

from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from chronicle_engine.connectors.files import store
from chronicle_engine.core.story.model import Report
from sources.entrypoints.cli.main import main as sources_main

from blueprint.core import checks, schema


def check(story: Any, facts: Any, path: Path, report: Report) -> None:
    """blueprint's checks, with the animation files they read beside the story."""
    files = {
        str(block["svg"]): store.read_text(path.parent / str(block["svg"]))
        for chapter in story.get("chapters", [])
        for block in chapter.get("blocks", [])
        if isinstance(block, dict)
        and block.get("type") == "architecture"
        and (path.parent / str(block.get("svg", ""))).is_file()
    }
    checks.architecture(story, files, report)
    checks.links(story, report)


def schema_parser(sub: Any) -> None:
    p = sub.add_parser("schema", help="an erd object from a schema export (CSV)")
    p.add_argument("export", type=Path, help=f"CSV with columns {', '.join(schema.COLUMNS)}")
    p.add_argument("--out", type=Path, help="write the erd object here (default: print it)")


def schema_run(args: argparse.Namespace) -> int:
    rows = list(csv.DictReader(io.StringIO(store.read_text(args.export))))
    data = schema.erd(rows)
    text = json.dumps(data, indent=1) + "\n"
    if args.out:
        store.write_text(args.out, text)
        print(
            f"wrote {args.out}: {len(data['entities'])} tables, {len(data['relations'])} relations"
        )
    else:
        print(text, end="")
    return 0


def sources_parser(sub: Any) -> None:
    p = sub.add_parser("sources", help="the linked sources command: detect, check, digest")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments for sources")


def sources_run(args: argparse.Namespace) -> int:
    return sources_main(args.args)
