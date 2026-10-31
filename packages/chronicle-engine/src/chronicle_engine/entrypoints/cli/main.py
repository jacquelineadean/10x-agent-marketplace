"""Command line: `python -m <plugin> <command>`, after the plugin's pack registers itself.

new    FOLDER           start a run folder: story.json and facts.json to fill in
check  STORY            validate structure, fact tokens, unsourced numbers and the theme
paint  STORY            make every image in story.art into OUT/art (with an art provider)
build  STORY            check, make the images that changed, and write OUT/artifact.html
                        and OUT/index.html
shoot  STORY            screenshot the built page at desktop and phone width
animate new|check|build standalone animations (see entrypoints/cli/animate.py)

A plugin adds its own commands through the registry.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from chronicle_engine import registry
from chronicle_engine.connectors.browser import shoot
from chronicle_engine.connectors.files import store
from chronicle_engine.connectors.video.encode import VideoError
from chronicle_engine.core.story import brand, model
from chronicle_engine.core.story import theme as theming
from chronicle_engine.core.story.facts import FactError
from chronicle_engine.core.story.render import Assets, render
from chronicle_engine.entrypoints.cli import animate, runs

BRAND_HELP = (
    "brand kit: run (brand.json in the run folder, the default), repo (.brand/brand.json "
    "at the git root), config (~/.config/chronicle/brand.json) or a path"
)
# What a missing NumPy or OpenCV means when no art provider says more.
MISSING = (
    "error: this command needs NumPy and OpenCV ({name} is missing). Run through the "
    "plugin's script with uv installed, or `pip install numpy opencv-python-headless`."
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog=registry.DEFAULTS.prog,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)
    provider = registry.art()
    for name in ("check", "paint", "build") if provider else ("check", "build"):
        cmd = sub.add_parser(name)
        cmd.add_argument("story", type=Path, help="path to story.json")
        cmd.add_argument(
            "--facts", type=Path, help="facts.json (default: facts.json beside the story)"
        )
        cmd.add_argument(
            "--out", type=Path, help="output folder (default: build/ beside the story)"
        )
        cmd.add_argument("--brand", default="run", help=BRAND_HELP)
        if name in ("paint", "build") and provider:
            cmd.add_argument("--scale", type=float, default=1.0, help="render size multiplier")
            cmd.add_argument("--force", action="store_true", help="repaint even if unchanged")
        if name == "build":
            if provider:
                cmd.add_argument(
                    "--no-paint", action="store_true", help="reuse existing paintings only"
                )
            cmd.add_argument(
                "--inline", action="store_true", help="also write single.html with images embedded"
            )
    for command in registry.COMMANDS.values():
        command.add_parser(sub)
    animate.add_parser(sub)
    new = sub.add_parser("new")
    new.add_argument("folder", type=Path, help="run folder to create, e.g. chronicle-runs/q4")
    new.add_argument("--title", default="", help="the page title")
    new.add_argument("--brand", default="run", help=BRAND_HELP + "; copied into the folder")
    new.add_argument(
        "--layout",
        choices=list(registry.LAYOUTS),
        default=registry.DEFAULTS.layout,
        help="how the story becomes a document",
    )
    shot = sub.add_parser("shoot")
    shot.add_argument("story", type=Path, help="path to story.json (its build/ is shot)")
    shot.add_argument("--out", type=Path, help="build folder (default: build/ beside the story)")
    shot.add_argument("--browser", help="Chromium or Chrome to use (default: first found)")
    shot.add_argument("--wait", type=int, default=4000, help="ms to let the page settle")
    args = parser.parse_args(argv)
    try:
        if args.command in registry.COMMANDS:
            return registry.COMMANDS[args.command].run(args)
        if args.command == "new":
            return _new(args.folder, args.title, args.brand, args.layout)
        if args.command == "shoot":
            return _shoot(args.out or args.story.parent / "build", args.browser, args.wait)
        if args.command == "animate":
            return animate.run(args)
        story = store.read_json(args.story)
        facts = _facts(args.story, story, args.facts)
        out = args.out or args.story.parent / "build"
        kit = runs.brand_kit(args.brand, args.story.parent)
        departures = brand.departures(story.get("theme"), kit) if kit else []
        if kit:
            story = {**story, "theme": brand.apply(story.get("theme"), kit)}
        report = model.check(story, facts)
        report.warnings.extend(departures)
        try:
            report.warnings.extend(theming.build(story.get("theme"), _fonts()).warnings)
        except theming.ThemeError as exc:
            report.errors.append(str(exc))
        policy = registry.POLICIES.get(registry.DEFAULTS.policy)
        if policy is not None:
            report.warnings.extend(policy(story.get("theme"), args.story))
        for extra in registry.CHECKS.values():
            extra(story, facts, args.story, report)
        files = _files(story, args.story.parent, report)
        texts: dict[str, str] = {}
        if provider is not None:
            texts = provider.drawings(story, args.story.parent, facts, report)
        elif story.get("art"):
            report.errors.append(
                "art names images, and this plugin makes none: remove art, hero.art and "
                "chapters[].art"
            )
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
        if provider is not None and (args.command == "paint" or not args.no_paint):
            provider.make(story, texts, out, args.scale, args.force)
        if args.command == "build":
            return _build(story, facts, files, out, args.inline)
        return 0
    except ModuleNotFoundError as exc:
        message = provider.missing_dependency if provider else MISSING
        print(message.format(name=exc.name), file=sys.stderr)
        return 2
    except (store.StoreError, FactError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except (shoot.BrowserError, VideoError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def _new(folder: Path, title: str, brand_choice: str, layout: str) -> int:
    """Start a run folder with a story to fill in, and keep it out of git."""
    story_path = folder / "story.json"
    if story_path.exists():
        print(f"error: {story_path} exists; pick another folder", file=sys.stderr)
        return 1
    if brand_choice != "run":
        kit = runs.brand_kit(brand_choice, folder.parent)
        store.write_json(folder / "brand.json", kit)
        print(f"copied the brand kit to {folder / 'brand.json'}")
    name = title or folder.name.replace("-", " ").title()
    store.write_json(story_path, _skeleton(name, layout))
    store.write_json(folder / "facts.json", {"derive": {}})
    for sub in registry.DEFAULTS.new_folders:
        (folder / sub).mkdir(parents=True, exist_ok=True)
    ignored = runs.ignore(folder)
    print(f"wrote {story_path} and {folder / 'facts.json'}")
    if ignored:
        print(f"added {ignored} to .gitignore")
    print(f"next: {registry.DEFAULTS.new_next}")
    return 0


def _skeleton(title: str, layout: str) -> dict[str, Any]:
    chapters = list(registry.LAYOUTS[layout].skeleton) or [
        {
            "id": "start",
            "short": "Start",
            "kicker": "",
            "title": "State this chapter's claim",
            "blocks": [{"type": "prose", "text": "Write the chapter here."}],
        }
    ]
    return {
        "schema_version": model.SCHEMA_VERSION,
        **({"layout": layout} if layout != "page" else {}),
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
        **({"art": {}} if registry.art() else {}),
        "hero": {},
        "chapters": chapters,
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
    return runs.load_facts(story_path, story, override, default_required=True)


def _fonts() -> Any:
    return store.fonts()


def _files(story: Mapping[str, Any], folder: Path, report: model.Report) -> dict[str, str]:
    """Read the files blocks name (widget scripts and styles, diagram SVG) and check them."""
    from chronicle_engine.core.story.diagram import DiagramError, sanitize

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
    for kind, keys in registry.FILES.items():
        for _, block in model.blocks_of(story, kind):
            for key in keys:
                if block.get(key):
                    texts[str(block[key])] = store.read_text(folder / str(block[key]))
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
    provider = registry.art()
    manifest = provider.manifest(out) if provider else {}
    missing = [k for k in story.get("art", {}) if k not in manifest]
    if missing:
        print(f"warning: no painting for {', '.join(missing)}; run paint first", file=sys.stderr)
    page = render(
        story,
        facts,
        manifest,
        Assets(parts=store.asset_files(registry.all_parts()), fonts=_fonts(), files=files),
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
