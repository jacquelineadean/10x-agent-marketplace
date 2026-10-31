"""briefing's commands and its check: `export` writes Slides or Dashboard content,
`slides` prints a built deck to a PNG per slide and a PDF.
"""

from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

from chronicle_engine.connectors.browser import devtools, shoot
from chronicle_engine.connectors.files import store
from chronicle_engine.core.story.model import Report
from chronicle_engine.entrypoints.cli import runs
from sources.entrypoints.cli.main import main as sources_main

from briefing.core import checks, export

# The deck's logical slide size; 13.333 x 7.5 inches is PowerPoint's 16:9 page.
SLIDE = (1600, 900)
PAGE_IN = (13.333, 7.5)


def check(story: Any, facts: Any, path: Path, report: Report) -> None:
    """briefing's checks, with the files they read beside the story."""
    checks.kpis(story, facts, report)
    checks.sliced(story, facts, report)
    checks.slides(story, report)
    queries = path.parent / "queries.json"
    if queries.is_file():
        entries = store.read_json(queries).get("queries", {})
        checks.stale(entries if isinstance(entries, dict) else {}, date.today(), report)
    files = {
        str(block["svg"]): store.read_text(path.parent / str(block["svg"]))
        for chapter in story.get("chapters", [])
        for block in chapter.get("blocks", [])
        if isinstance(block, dict)
        and block.get("type") == "animation"
        and block.get("svg")
        and (path.parent / str(block["svg"])).is_file()
    }
    checks.animations(story, files, report)


def export_parser(sub: Any) -> None:
    p = sub.add_parser("export", help="write a deck or dashboard as Slides or Dashboard content")
    p.add_argument("story", type=Path, help="path to story.json")
    p.add_argument("--to", choices=("slides", "dashboard"), required=True)
    p.add_argument("--out", type=Path, help="build folder (default: build/ beside the story)")


def export_run(args: argparse.Namespace) -> int:
    story = store.read_json(args.story)
    facts = runs.load_facts(args.story, story, None, default_required=True)
    data = export.slides(story, facts) if args.to == "slides" else export.dashboard(story, facts)
    out = (args.out or args.story.parent / "build") / f"{args.to}.json"
    store.write_text(out, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"wrote {out}")
    if args.to == "slides":
        print(f"next: briefing slides {args.story} --png, for the slide images it names")
    return 0


def slides_parser(sub: Any) -> None:
    p = sub.add_parser("slides", help="print a built deck: a PNG per slide and a PDF")
    p.add_argument("story", type=Path, help="path to story.json (its build/ is printed)")
    p.add_argument("--out", type=Path, help="build folder (default: build/ beside the story)")
    p.add_argument("--png", action="store_true", help="write build/slides/slide-NN.png")
    p.add_argument("--pdf", action="store_true", help="write build/deck.pdf")
    p.add_argument("--browser", help="Chromium or Chrome to use (default: first found)")


def slides_run(args: argparse.Namespace) -> int:
    out = args.out or args.story.parent / "build"
    page = out / "index.html"
    if not page.exists():
        print(f"error: {page} does not exist; run build first")
        return 1
    if not (args.png or args.pdf):
        print("error: pass --png, --pdf or both")
        return 1
    width, height = SLIDE
    with devtools.Capture(shoot.find(args.browser)) as capture:
        capture.open(page.resolve().as_uri() + "#still", width, height)
        count = int(capture.evaluate("document.querySelectorAll('.deck .slide').length"))
        if args.png:
            for n in range(count):
                capture.evaluate(
                    f"window.briefingDeck.show({n}, true);"
                    " new Promise(r => requestAnimationFrame(() => setTimeout(r, 150)))"
                )
                image = out / "slides" / f"slide-{n + 1:02d}.png"
                store.write_bytes(image, capture.png(width, height))
            print(f"wrote {count} slide images to {out / 'slides'}")
        if args.pdf:
            store.write_bytes(out / "deck.pdf", capture.pdf(*PAGE_IN))
            print(f"wrote {out / 'deck.pdf'} ({count} pages)")
    return 0


def sources_parser(sub: Any) -> None:
    p = sub.add_parser("sources", help="the linked sources command: detect, check, digest")
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments for sources")


def sources_run(args: argparse.Namespace) -> int:
    return sources_main(args.args)
