"""`chronicle widgets`: list the widget library, copy a widget into a run, save one to it."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from chronicle_engine.config import settings
from chronicle_engine.connectors.files import store
from chronicle_engine.core.story.model import lint_style, lint_widget

from chronicle.core.story import library

BUNDLED = Path(__file__).resolve().parents[4] / "widgets"


def roots() -> dict[str, Path]:
    """Library folders by where they are, in the order a name is looked up."""
    found: dict[str, Path] = {}
    here = Path.cwd().resolve()
    repo = next((p for p in (here, *here.parents) if (p / ".git").exists()), None)
    if repo is not None:
        found["repo"] = repo / ".chronicle" / "widgets"
    found["config"] = settings.brand_config_path().parent / "widgets"
    found["bundled"] = BUNDLED
    return found


def _entries() -> dict[str, tuple[str, Path]]:
    """Every library widget by name; an earlier folder hides a later one of the same name."""
    out: dict[str, tuple[str, Path]] = {}
    for where, root in roots().items():
        if not root.is_dir():
            continue
        for folder in sorted(root.iterdir()):
            if (folder / "widget.js").is_file() and folder.name not in out:
                out[folder.name] = (where, folder)
    return out


def _problems(script: str, style: str) -> list[str]:
    return lint_widget(script) + lint_style(style)


def parser(sub: Any) -> None:
    p = sub.add_parser("widgets", help="the widget library: list, add to a run, save from one")
    act = p.add_subparsers(dest="action", required=True)
    act.add_parser("list", help="every library widget and where it lives")
    add = act.add_parser("add", help="copy a library widget into a run folder")
    add.add_argument("name")
    add.add_argument("folder", type=Path, help="the run folder")
    add.add_argument("--force", action="store_true", help="replace the run's copy")
    save = act.add_parser("save", help="save a run's widget to the library")
    save.add_argument("folder", type=Path, help="the run folder")
    save.add_argument("name")
    save.add_argument("--to", choices=("repo", "config"), default="repo")
    save.add_argument("--summary", default="", help="what the widget does, in one sentence")
    save.add_argument("--force", action="store_true", help="replace a library widget")


def _list() -> int:
    for name, (where, folder) in sorted(_entries().items()):
        meta = store.read_json(folder / "widget.json") if (folder / "widget.json").is_file() else {}
        print(f"{name} ({where}): {meta.get('summary', '')}")
    return 0


def _add(name: str, folder: Path, force: bool) -> int:
    found = _entries().get(name)
    if found is None:
        print(f"error: no library widget {name!r}; run `widgets list`", file=sys.stderr)
        return 1
    where, source = found
    meta = store.read_json(source / "widget.json")
    script = store.read_text(source / "widget.js")
    style = store.read_text(source / "widget.css") if (source / "widget.css").is_file() else ""
    problems = library.check_meta(name, meta) + _problems(script, style)
    target = folder / "widgets" / f"{name}.js"
    if target.exists() and not force:
        problems.append(f"{target} exists; pass --force to replace it")
    for line in problems:
        print(f"error: {line}", file=sys.stderr)
    if problems:
        return 1
    store.write_text(target, script)
    if style:
        store.write_text(target.with_suffix(".css"), style)
    print(f"copied {name} from the {where} library into {target.parent}")
    print("add this block to a chapter, then change its data:")
    print(json.dumps(library.block(name, meta, bool(style)), indent=1, ensure_ascii=False))
    return 0


def _story_block(folder: Path, name: str) -> Mapping[str, Any]:
    story = store.read_json(folder / "story.json")
    for chapter in story.get("chapters", []):
        for block in chapter.get("blocks", []):
            if (
                isinstance(block, Mapping)
                and block.get("type") == "widget"
                and block.get("name") == name
            ):
                return block
    return {}


def _save(folder: Path, name: str, to: str, summary: str, force: bool) -> int:
    script = store.read_text(folder / "widgets" / f"{name}.js")
    style_path = folder / "widgets" / f"{name}.css"
    style = store.read_text(style_path) if style_path.is_file() else ""
    meta = library.meta_from(_story_block(folder, name), summary)
    target = roots()[to] / name if to in roots() else None
    problems = library.check_meta(name, meta) + _problems(script, style)
    if target is None:
        problems.append("there is no repository here; save --to config")
    elif target.exists() and not force:
        problems.append(f"{target} exists; pass --force to replace it")
    for line in problems:
        print(f"error: {line}", file=sys.stderr)
    if problems or target is None:
        return 1
    store.write_text(target / "widget.js", script)
    if style:
        store.write_text(target / "widget.css", style)
    store.write_json(target / "widget.json", meta)
    print(f"saved {name} to {target}")
    return 0


def run(args: argparse.Namespace) -> int:
    if args.action == "list":
        return _list()
    if args.action == "add":
        return _add(args.name, args.folder, args.force)
    return _save(args.folder, args.name, args.to, args.summary, args.force)
