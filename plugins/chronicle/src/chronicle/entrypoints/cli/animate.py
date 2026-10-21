"""Command line for standalone animations: `python -m chronicle animate <command>`.

new    FOLDER        start a run folder with animation.json for a tad, diagram or scene
check  ANIMATION     validate the animation, its ids, fact tokens and theme
build  ANIMATION     write animation.svg, embed.html and index.html, and with a browser
                     poster.png, steps.png and the GIF or video formats asked for
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping
from contextlib import ExitStack
from pathlib import Path
from typing import Any

from chronicle.connectors.browser import devtools, shoot
from chronicle.connectors.files import store
from chronicle.connectors.video import encode
from chronicle.core.motion import embed, model
from chronicle.core.motion.render import Animation, Sources, check, render
from chronicle.core.story import derive
from chronicle.core.story import model as story_model
from chronicle.entrypoints.cli import runs
from chronicle.entrypoints.cli.art import ART_DIR, MANIFEST, drawings, paint

FORMATS = ("svg", "html", "png", "gif", "mp4", "webm")
DEFAULT_FORMATS = "svg,html,png,gif"
SEEK = (
    "document.documentElement.style.setProperty('--seek', '{t:.4f}s');"
    " new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))"
)


def add_parser(sub: Any) -> None:
    """Register `animate` and its commands on the main parser."""
    animate = sub.add_parser("animate", help="standalone animations: tad, diagram or scene")
    commands = animate.add_subparsers(dest="action", required=True)
    new = commands.add_parser("new")
    new.add_argument("folder", type=Path, help="run folder to create, e.g. chronicle-runs/flow")
    new.add_argument("--kind", choices=model.KINDS, default="tad")
    new.add_argument("--title", default="", help="the animation's title")
    for name in ("check", "build"):
        cmd = commands.add_parser(name)
        cmd.add_argument("animation", type=Path, help="path to animation.json")
        cmd.add_argument("--facts", type=Path, help="facts.json (default: as the file names)")
        if name == "build":
            cmd.add_argument("--out", type=Path, help="output folder (default: build/ beside it)")
            cmd.add_argument(
                "--formats",
                default=DEFAULT_FORMATS,
                help=f"comma list of {', '.join(FORMATS)} (default {DEFAULT_FORMATS})",
            )
            cmd.add_argument("--fps", type=float, default=30.0, help="video frames a second")
            cmd.add_argument("--gif-fps", type=float, default=15.0, help="GIF frames a second")
            cmd.add_argument("--gif-width", type=int, default=960, help="GIF width in pixels")
            cmd.add_argument(
                "--theme", choices=("light", "dark"), default="light", help="theme of raster files"
            )
            cmd.add_argument("--browser", help="Chromium or Chrome to use (default: first found)")
            cmd.add_argument(
                "--force", action="store_true", help="repaint a scene even if unchanged"
            )


def run(args: argparse.Namespace) -> int:
    if args.action == "new":
        return _new(args.folder, args.kind, args.title)
    anim = store.read_json(args.animation)
    if not isinstance(anim, Mapping):
        print("error: an animation must be a JSON object", file=sys.stderr)
        return 1
    facts = _facts(args.animation, anim, args.facts)
    folder = args.animation.parent
    sources = Sources(drawing=_drawing(anim, folder))
    report = check(anim, facts, store.fonts(), sources)
    for warning in report.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    for error in report.errors:
        print(f"error: {error}", file=sys.stderr)
    if not report.ok:
        print(f"{len(report.errors)} error(s); nothing written.", file=sys.stderr)
        return 1
    if args.action == "check":
        print(f"ok: {args.animation} ({len(report.warnings)} warning(s))")
        return 0
    formats = [f.strip() for f in str(args.formats).split(",") if f.strip()]
    unknown = sorted(set(formats) - set(FORMATS))
    if unknown:
        print(
            f"error: unknown format {', '.join(unknown)}; use {', '.join(FORMATS)}", file=sys.stderr
        )
        return 1
    out = args.out or folder / "build"
    if anim.get("kind") == "scene":
        sources = _painted(anim, folder, facts, out, args.force)
    css = store.asset_parts("motion", ".css") + store.asset("css/40-drawn.css")
    result = render(anim, facts, store.fonts(), css, sources)
    for warning in result.warnings:
        print(f"warning: {warning}", file=sys.stderr)
    return _write(result, out, formats, args)


# ------------------------------------------------------------------------ input
def _facts(path: Path, anim: Mapping[str, Any], override: Path | None) -> Any:
    if override:
        raw = store.read_json(override)
    elif "facts_file" in anim:
        raw = store.read_json(path.parent / str(anim["facts_file"]))
    elif (path.parent / "facts.json").exists():
        raw = store.read_json(path.parent / "facts.json")
    else:
        raw = {}
    if not isinstance(raw, Mapping):
        raise store.StoreError("the facts file must hold a JSON object")
    return derive.apply(raw)


def _drawing(anim: Mapping[str, Any], folder: Path) -> str:
    """The SVG a diagram plays, or the drawing a scene paints, inline or from its file."""
    kind = anim.get("kind")
    body = anim.get(str(kind))
    if not isinstance(body, Mapping):
        return ""
    if kind == "diagram":
        source = str(body.get("svg", ""))
    elif kind == "scene" and isinstance(body.get("art"), Mapping):
        source = str(body["art"].get("svg", ""))
    else:
        return ""
    if not source:
        if kind == "diagram":
            raise store.StoreError("diagram.svg is required: a drawing file or inline <svg>")
        return ""
    return source if source.lstrip().startswith("<svg") else store.read_text(folder / source)


def _painted(
    anim: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], out: Path, force: bool
) -> Sources:
    """Paint the scene's art (once; unchanged art is kept) and embed its images."""
    story = {"art": {"scene": anim["scene"]["art"]}}
    report = story_model.Report()
    texts = drawings(story, folder, facts, report)
    if not report.ok:
        raise ValueError("; ".join(report.errors))
    paint(story, texts, out, 1.0, force)
    entry = store.read_json(out / ART_DIR / MANIFEST)["scene"]
    files = [str(entry["file"]), *(str(layer["file"]) for layer in entry.get("layers", []))]
    images = {f: store.data_uri(out / f) for f in files}
    return Sources(drawing=texts.get("scene", ""), painting=entry, images=images)


# ----------------------------------------------------------------------- output
def _write(result: Animation, out: Path, formats: list[str], args: argparse.Namespace) -> int:
    plan = result.plan
    svg_path = out / "animation.svg"
    store.write_text(svg_path, result.svg)
    print(f"wrote {svg_path} ({len(result.svg) // 1024} KB, {plan.duration:.1f} s loop)")
    if "html" in formats:
        fragment = embed.figure(plan, result.svg)
        store.write_text(out / "embed.html", fragment)
        store.write_text(out / "index.html", embed.page(plan, fragment))
        print(f"wrote {out / 'embed.html'} (paste into a page) and {out / 'index.html'}")
    raster = [f for f in formats if f in ("png", "gif", "mp4", "webm")]
    if not raster:
        return 0
    program = encode.ffmpeg()
    if "mp4" in raster and program is None:
        print("warning: mp4 needs ffmpeg on PATH; writing webm instead", file=sys.stderr)
        raster = [f if f != "mp4" else "webm" for f in raster]
    page = out / "capture.html"
    store.write_text(page, embed.capture(result.svg))
    try:
        with devtools.Capture(shoot.find(args.browser)) as cap:
            cap.open(page.resolve().as_uri(), plan.width, plan.height)
            if args.theme == "dark":
                dark = [{"name": "prefers-color-scheme", "value": "dark"}]
                cap.send("Emulation.setEmulatedMedia", {"features": dark})
            _rasters(cap, result, out, raster, args, program)
    finally:
        page.unlink(missing_ok=True)
    print("look at steps.png with the Read tool before sharing")
    return 0


def _frame(cap: devtools.Capture, plan: model.Plan, t: float) -> Any:
    cap.evaluate(SEEK.format(t=t))
    return store.decode_png(cap.png(plan.width, plan.height))


def _rasters(
    cap: devtools.Capture,
    result: Animation,
    out: Path,
    formats: list[str],
    args: argparse.Namespace,
    program: str | None,
) -> None:
    from chronicle.core.motion import frames, gif

    plan = result.plan
    marks = [_frame(cap, plan, t) for t in frames.checkpoints(plan)]
    size = store.write_png(out / "steps.png", frames.sheet(marks))
    print(f"wrote {out / 'steps.png'} ({len(marks)} steps, {size // 1024} KB)")
    if "png" in formats:
        cap.evaluate("document.documentElement.classList.add('still')")
        size = store.write_png(out / "poster.png", _frame(cap, plan, 0.0))
        cap.evaluate("document.documentElement.classList.remove('still')")
        print(f"wrote {out / 'poster.png'} (the still: the whole picture, {size // 1024} KB)")
    video = [f for f in formats if f in ("mp4", "webm")]
    wants_gif = "gif" in formats
    if not video and not wants_gif:
        return
    fps = args.fps if video else args.gif_fps
    every = max(1, round(fps / args.gif_fps)) if video else 1
    writer = None
    if wants_gif:
        width = min(args.gif_width, plan.width)
        shots = [frames.scaled(_frame(cap, plan, t), width) for t in frames.samples(plan)]
        height = shots[0].shape[0]
        writer = gif.Writer(width, height, gif.palette(shots), plan.loop)
    sinks: list[encode.Mp4 | encode.Webm] = []
    if "mp4" in video and program is not None:
        sinks.append(encode.Mp4(program, out / "animation.mp4", plan.width, plan.height, fps))
    if "webm" in video:
        sinks.append(encode.Webm(out / "animation.webm", plan.width, plan.height, fps))
    moments = frames.times(plan, fps)
    print(f"capturing {len(moments)} frames at {fps:g} fps")
    with ExitStack() as stack:
        for sink in sinks:
            stack.enter_context(sink)
        for i, t in enumerate(moments):
            image = _frame(cap, plan, t)
            for sink in sinks:
                sink.add(image)
            if writer is not None and i % every == 0:
                writer.add(frames.scaled(image, writer.width), every / fps)
    for sink in sinks:
        print(f"wrote {sink.path} ({sink.path.stat().st_size // 1024} KB)")
    if writer is not None:
        data = writer.finish()
        store.write_bytes(out / "animation.gif", data)
        print(f"wrote {out / 'animation.gif'} ({len(data) // 1024} KB, {writer.width} px wide)")


# -------------------------------------------------------------------------- new
def _new(folder: Path, kind: str, title: str) -> int:
    path = folder / "animation.json"
    if path.exists():
        print(f"error: {path} exists; pick another folder", file=sys.stderr)
        return 1
    name = title or folder.name.replace("-", " ").title()
    store.write_json(path, _skeleton(kind, name))
    store.write_json(folder / "facts.json", {"derive": {}})
    if kind == "diagram":
        store.write_text(folder / "drawing.svg", DRAWING)
    print(f"wrote {path} and {folder / 'facts.json'}")
    ignored = runs.ignore(folder)
    if ignored:
        print(f"added {ignored} to .gitignore")
    print(f"next: {NEXT[kind]}, then the steps; run animate check, then animate build")
    return 0


def _skeleton(kind: str, title: str) -> dict[str, Any]:
    bodies: dict[str, dict[str, Any]] = {
        "tad": {
            "direction": "right",
            "groups": [],
            "nodes": [{"id": "client", "label": "Client", "kind": "client"}],
            "edges": [],
            "flows": [],
        },
        "diagram": {"svg": "drawing.svg"},
        "scene": {"art": {"svg": "drawing.svg", "seed": 1, "alt": ""}, "spots": []},
    }
    body = bodies[kind]
    return {
        "schema_version": model.SCHEMA_VERSION,
        "kind": kind,
        "meta": {"title": title, "kicker": "", "description": "", "credit": "", "sources": []},
        "theme": {"concept": ""},
        "frame": {"size": "16:9"},
        kind: body,
        "steps": [],
    }


NEXT = {
    "tad": "write the nodes, groups, edges and flows",
    "diagram": "draw drawing.svg with an id on every part",
    "scene": "draw drawing.svg as a story plate, with a data-anchor for each spot",
}

DRAWING = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 400">
  <rect id="start" class="box" x="40" y="160" width="180" height="80" rx="10"/>
  <text x="130" y="206" text-anchor="middle" class="title">Start</text>
  <path id="hop" class="line" d="M220 200 H740"/>
  <rect id="end" class="box accent" x="740" y="160" width="180" height="80" rx="10"/>
  <text x="830" y="206" text-anchor="middle" class="title">End</text>
</svg>
"""
