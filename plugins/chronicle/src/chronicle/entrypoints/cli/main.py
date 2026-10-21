"""Command line: `python -m chronicle <command>`.

new    FOLDER           start a run folder: story.json and facts.json to fill in
check  STORY            validate structure, fact tokens, unsourced numbers and the theme
paint  STORY            paint every scene in story.art into OUT/art (needs NumPy and OpenCV)
build  STORY            check, paint what changed, and write OUT/artifact.html + OUT/index.html
shoot  STORY            screenshot the built page at desktop and phone width
motifs                  list presets, motifs and their parameters for writing scenes
animate new|check|build standalone animations (see entrypoints/cli/animate.py)
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from chronicle.connectors.browser import shoot
from chronicle.connectors.files import store
from chronicle.connectors.video.encode import VideoError
from chronicle.core.story import derive, model
from chronicle.core.story import theme as theming
from chronicle.core.story.facts import FactError
from chronicle.core.story.render import Assets, render
from chronicle.entrypoints.cli import animate, runs
from chronicle.entrypoints.cli.art import ART_DIR, MANIFEST, drawings, paint

EXAMPLES = Path(__file__).resolve().parents[4] / "examples"
# Other pages a new theme is compared with: the bundled examples and up to this many
# sibling run folders.
MAX_SIBLINGS = 40


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chronicle", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "paint", "build"):
        cmd = sub.add_parser(name)
        cmd.add_argument("story", type=Path, help="path to story.json")
        cmd.add_argument(
            "--facts", type=Path, help="facts.json (default: facts.json beside the story)"
        )
        cmd.add_argument(
            "--out", type=Path, help="output folder (default: build/ beside the story)"
        )
        if name in ("paint", "build"):
            cmd.add_argument("--scale", type=float, default=1.0, help="render size multiplier")
            cmd.add_argument("--force", action="store_true", help="repaint even if unchanged")
        if name == "build":
            cmd.add_argument(
                "--no-paint", action="store_true", help="reuse existing paintings only"
            )
            cmd.add_argument(
                "--inline", action="store_true", help="also write single.html with images embedded"
            )
    sub.add_parser("motifs")
    animate.add_parser(sub)
    new = sub.add_parser("new")
    new.add_argument("folder", type=Path, help="run folder to create, e.g. chronicle-runs/q4")
    new.add_argument("--title", default="", help="the page title")
    shot = sub.add_parser("shoot")
    shot.add_argument("story", type=Path, help="path to story.json (its build/ is shot)")
    shot.add_argument("--out", type=Path, help="build folder (default: build/ beside the story)")
    shot.add_argument("--browser", help="Chromium or Chrome to use (default: first found)")
    shot.add_argument("--wait", type=int, default=4000, help="ms to let the page settle")
    args = parser.parse_args(argv)
    try:
        if args.command == "motifs":
            return _motifs()
        if args.command == "new":
            return _new(args.folder, args.title)
        if args.command == "shoot":
            return _shoot(args.out or args.story.parent / "build", args.browser, args.wait)
        if args.command == "animate":
            return animate.run(args)
        story = store.read_json(args.story)
        facts = _facts(args.story, story, args.facts)
        out = args.out or args.story.parent / "build"
        report = model.check(story, facts)
        try:
            report.warnings.extend(theming.build(story.get("theme"), _fonts()).warnings)
        except theming.ThemeError as exc:
            report.errors.append(str(exc))
        report.warnings.extend(theming.review(story.get("theme"), _other_themes(args.story)))
        files = _files(story, args.story.parent, report)
        texts = drawings(story, args.story.parent, facts, report)
        for warning in report.warnings:
            print(f"warning: {warning}", file=sys.stderr)
        for error in report.errors:
            print(f"error: {error}", file=sys.stderr)
        if not report.ok:
            print(f"{len(report.errors)} error(s); nothing written.", file=sys.stderr)
            return 1
        if args.command == "check":
            print(f"ok: {args.story} ({len(report.warnings)} warning(s))")
            return 0
        if args.command == "paint" or not args.no_paint:
            paint(story, texts, out, args.scale, args.force)
        if args.command == "build":
            return _build(story, facts, files, out, args.inline)
        return 0
    except ModuleNotFoundError as exc:
        print(
            f"error: painting needs NumPy and OpenCV ({exc.name} is missing). Run through "
            "scripts/chronicle with uv installed, or `pip install numpy opencv-python-headless`; "
            "`build --no-paint` renders the page with the paintings already made.",
            file=sys.stderr,
        )
        return 2
    except (store.StoreError, FactError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (shoot.BrowserError, VideoError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _other_themes(story_path: Path) -> dict[str, Any]:
    """Themes of the bundled examples and of sibling run folders, to compare a page with."""
    here = story_path.resolve()
    paths = sorted(EXAMPLES.glob("*/story.json")) if EXAMPLES.is_dir() else []
    paths += sorted(here.parent.parent.glob("*/story.json"))[:MAX_SIBLINGS]
    themes: dict[str, Any] = {}
    for path in paths:
        if path.resolve() == here:
            continue
        try:
            other = store.read_json(path)
        except store.StoreError:
            continue
        if isinstance(other, Mapping) and isinstance(other.get("theme"), Mapping):
            label = "example " if path.parent.parent == EXAMPLES else ""
            themes[f"{label}{path.parent.name}"] = other["theme"]
    return themes


def _new(folder: Path, title: str) -> int:
    """Start a run folder with a story to fill in, and keep it out of git."""
    story_path = folder / "story.json"
    if story_path.exists():
        print(f"error: {story_path} exists; pick another folder", file=sys.stderr)
        return 1
    name = title or folder.name.replace("-", " ").title()
    store.write_json(story_path, _skeleton(name))
    store.write_json(folder / "facts.json", {"derive": {}})
    for sub in (ART_DIR, "diagrams", "widgets"):
        (folder / sub).mkdir(parents=True, exist_ok=True)
    ignored = runs.ignore(folder)
    print(f"wrote {story_path} and {folder / 'facts.json'}")
    if ignored:
        print(f"added {ignored} to .gitignore")
    print("next: do the design pass (references/identity.md), then fill theme.concept first")
    return 0


def _skeleton(title: str) -> dict[str, Any]:
    return {
        "schema_version": model.SCHEMA_VERSION,
        "meta": {
            "title": title,
            "kicker": "",
            "dek": "",
            "byline": [],
            "description": "",
            "colophon": "",
        },
        "theme": {"concept": ""},
        "sources": [],
        "art": {},
        "hero": {},
        "chapters": [
            {
                "id": "start",
                "short": "Start",
                "kicker": "",
                "title": "State this chapter's claim",
                "blocks": [{"type": "prose", "text": "Write the chapter here."}],
            }
        ],
    }


def _shoot(out: Path, browser: str | None, wait: int) -> int:
    page = out / "index.html"
    if not page.exists():
        print(f"error: {page} does not exist; run build first", file=sys.stderr)
        return 1
    found = shoot.find(browser)
    for name, size in shoot.SIZES.items():
        image = shoot.shoot(found, page, out / "shots" / f"{name}.png", size, wait)
        print(f"wrote {image} ({size[0]} px wide)")
    print("look at both images with the Read tool before publishing")
    return 0


def _facts(story_path: Path, story: Mapping[str, Any], override: Path | None) -> Any:
    if override:
        raw = store.read_json(override)
    elif isinstance(story.get("facts"), Mapping):
        raw = story["facts"]
    else:
        raw = store.read_json(story_path.parent / str(story.get("facts_file", "facts.json")))
    if not isinstance(raw, Mapping):
        raise store.StoreError("the facts file must hold a JSON object")
    return derive.apply(raw)


def _fonts() -> Any:
    return store.fonts()


def _files(story: Mapping[str, Any], folder: Path, report: model.Report) -> dict[str, str]:
    """Read the files blocks name (widget scripts and styles, diagram SVG) and check them."""
    from chronicle.core.story.diagram import DiagramError, sanitize

    texts: dict[str, str] = {}
    for where, block in model.blocks_of(story, "widget"):
        for key in ("script", "style"):
            path = str(block.get(key, ""))
            if not path:
                continue
            source = store.read_text(folder / path)
            problems = model.lint_widget(source) if key == "script" else model.lint_style(source)
            for problem in problems:
                report.errors.append(f"{where} ({path}): {problem}")
            texts[path] = source
    for where, block in model.blocks_of(story, "diagram"):
        path = str(block.get("svg", ""))
        source = path if path.lstrip().startswith("<svg") else store.read_text(folder / path)
        try:
            sanitize(source, "check")
        except DiagramError as exc:
            report.errors.append(f"{where} ({path[:60]}): {exc}")
        texts[path] = source
    return texts


def _build(
    story: Mapping[str, Any], facts: Any, files: Mapping[str, str], out: Path, inline: bool
) -> int:
    manifest_path = out / ART_DIR / MANIFEST
    manifest = store.read_json(manifest_path) if manifest_path.exists() else {}
    missing = [k for k in story.get("art", {}) if k not in manifest]
    if missing:
        print(f"warning: no painting for {', '.join(missing)}; run paint first", file=sys.stderr)
    page = render(
        story,
        facts,
        manifest,
        Assets(
            css=store.asset_parts("css", ".css"),
            js=_runtime(),
            fonts=_fonts(),
            files=files,
        ),
    )
    store.write_text(out / "artifact.html", page.fragment)
    store.write_text(out / "index.html", page.document)
    print(f"wrote {out / 'artifact.html'} (publish this) and {out / 'index.html'} (open locally)")
    files = {rel: str(out / rel) for rel in page.art_files}
    store.write_json(out / "publish-files.json", files)
    print(f"{len(files)} image file(s) to publish alongside; map in {out / 'publish-files.json'}")
    if inline:
        single = page.document
        for rel in page.art_files:
            single = single.replace(f'src="{rel}"', f'src="{store.data_uri(out / rel)}"')
        store.write_text(out / "single.html", single)
        print(f"wrote {out / 'single.html'} with images embedded")
    return 0


def _runtime() -> str:
    """The page script: every js/ part inside one function, so parts share helpers."""
    return "(function () {\n" + store.asset_parts("js", ".js") + "\n})();"


def _motifs() -> int:
    from chronicle.core.watercolor import presets, scene  # needs NumPy and OpenCV

    print('Presets (art spec: {"preset": NAME, "params": {...}}):')
    for name, fn in presets.PRESETS.items():
        doc = (fn.__doc__ or "").strip().splitlines()[0]
        print(f"  {name}: {doc}")
    print('\nMotifs and brush primitives (art spec elements: {"motif": NAME, ...}):')
    for name in scene.motif_names():
        print(f"  {name}({scene.motif_signature(name)})")
    return 0
