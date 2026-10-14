"""Command line: `python -m chronicle <command>`.

check  STORY            validate structure, fact tokens and unsourced numbers
paint  STORY            paint every scene in story.art into OUT/art (needs NumPy and OpenCV)
build  STORY            check, paint what changed, and write OUT/artifact.html + OUT/index.html
motifs                  list presets, motifs and their parameters for writing scenes
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from chronicle.connectors.files import store
from chronicle.core.story import derive, model
from chronicle.core.story.facts import FactError
from chronicle.core.story.render import Assets, render

ART_DIR = "art"
MANIFEST = "manifest.json"


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
    args = parser.parse_args(argv)
    try:
        if args.command == "motifs":
            return _motifs()
        story = store.read_json(args.story)
        facts = _facts(args.story, story, args.facts)
        out = args.out or args.story.parent / "build"
        report = model.check(story, facts)
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
            _paint(story, out, args.scale, args.force)
        if args.command == "build":
            return _build(story, facts, out, args.inline)
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


def _engine_digest() -> str:
    """Fingerprint of the painting code, so a change to a motif repaints its scenes."""
    folder = Path(__file__).resolve().parents[2] / "core" / "watercolor"
    digest = hashlib.sha256()
    for path in sorted(folder.rglob("*.py")):
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


def _scene_hash(spec: Mapping[str, Any], scale: float, engine: str) -> str:
    raw = json.dumps({"spec": spec, "scale": scale, "engine": engine}, sort_keys=True)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _paint(story: Mapping[str, Any], out: Path, scale: float, force: bool) -> None:
    from chronicle.core.watercolor import presets, scene  # needs NumPy and OpenCV

    art_dir = out / ART_DIR
    manifest_path = art_dir / MANIFEST
    old: dict[str, Any] = {}
    if manifest_path.exists():
        old = store.read_json(manifest_path)
    manifest: dict[str, Any] = {}
    engine = _engine_digest()
    for key, spec in dict(story.get("art", {})).items():
        digest = _scene_hash(spec, scale, engine)
        prior = old.get(key)
        if not force and prior and prior.get("hash") == digest and (out / prior["file"]).exists():
            manifest[key] = prior
            print(f"art: {key} unchanged")
            continue
        if "preset" in spec:
            painting = presets.paint_preset(str(spec["preset"]), spec.get("params", {}), scale)
        else:
            painting = scene.paint_elements(spec, scale)
        base_rel = f"{ART_DIR}/{key}.webp"
        size = store.write_webp(out / base_rel, painting.base)
        entry: dict[str, Any] = {
            "hash": digest,
            "file": base_rel,
            "width": painting.width,
            "height": painting.height,
            "anchors": {k: [round(v[0], 1), round(v[1], 1)] for k, v in painting.anchors.items()},
            "layers": [],
        }
        for layer in painting.layers:
            rel = f"{ART_DIR}/{key}--{layer.name}.webp"
            size += store.write_webp(out / rel, layer.image)
            entry["layers"].append(
                {
                    "name": layer.name,
                    "file": rel,
                    "box": list(layer.box),
                    "motion": layer.motion,
                    "travel": layer.travel,
                }
            )
        manifest[key] = entry
        print(f"art: {key} painted, {size // 1024} KB")
    store.write_json(manifest_path, manifest)


def _build(story: Mapping[str, Any], facts: Any, out: Path, inline: bool) -> int:
    manifest_path = out / ART_DIR / MANIFEST
    manifest = store.read_json(manifest_path) if manifest_path.exists() else {}
    missing = [k for k in story.get("art", {}) if k not in manifest]
    if missing:
        print(f"warning: no painting for {', '.join(missing)}; run paint first", file=sys.stderr)
    page = render(
        story,
        facts,
        manifest,
        Assets(css=store.asset("chronicle.css"), js=store.asset("chronicle.js")),
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
