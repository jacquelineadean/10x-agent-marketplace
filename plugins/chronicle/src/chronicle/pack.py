"""chronicle's registrations with the engine.

Plates, the painter, the page chrome, scenes, the sameness review and the `motifs` and
`research` commands. TADs moved to blueprint (RFC-0007 phase 4).

Importing this module registers everything once; `python -m chronicle` imports it before
running the engine's command line.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from importlib import resources
from pathlib import Path
from typing import Any

from chronicle_engine import registry
from chronicle_engine.connectors.files import store
from chronicle_engine.core.motion import diagram as diagram_kind
from chronicle_engine.core.motion import stage
from chronicle_engine.core.motion.model import ACTIONS, Plan
from chronicle_engine.core.motion.timeline import Timeline
from chronicle_engine.core.story import model
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Builder
from chronicle_engine.registry import Kind, Prepared, Sources

from chronicle.core.motion import scene
from chronicle.core.story import checks, chrome, game, panorama, plates, review, rooms, tour
from chronicle.core.watercolor.svg.parse import GAITS, Drawing, SvgError, parse
from chronicle.entrypoints.cli import art, commands, widgets

EXAMPLES = Path(__file__).resolve().parents[2] / "examples"
# Other pages a new theme is compared with: the bundled examples and up to this many
# sibling run folders.
MAX_SIBLINGS = 40


# ----------------------------------------------------------------------- art
class Painter:
    """chronicle's art provider: SVG drawings and presets painted in watercolor."""

    missing_dependency = (
        "error: painting needs NumPy and OpenCV ({name} is missing). Run through "
        "scripts/chronicle with uv installed, or `pip install numpy opencv-python-headless`; "
        "`build --no-paint` renders the page with the paintings already made."
    )

    def drawings(
        self, story: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], report: Report
    ) -> dict[str, str]:
        return art.drawings(story, folder, facts, report)

    def make(
        self,
        story: Mapping[str, Any],
        texts: Mapping[str, str],
        out: Path,
        scale: float,
        force: bool,
    ) -> None:
        art.paint(story, texts, out, scale, force)

    def manifest(self, out: Path) -> dict[str, Any]:
        path = out / art.ART_DIR / art.MANIFEST
        found = store.read_json(path) if path.exists() else {}
        return dict(found) if isinstance(found, Mapping) else {}

    def figure(self, b: Builder, key: str, caption: Any, width: str, spots: Any) -> str:
        return plates.plate(b, key, caption, width, spots)

    def font_needs(self, manifest: Mapping[str, Any]) -> frozenset[str]:
        styles = {
            str(lab.get("style", "hand"))
            for entry in manifest.values()
            if isinstance(entry, Mapping)
            for lab in entry.get("labels", [])
        }
        needs = set()
        if "hand" in styles:
            needs.add("hand")
        if styles & {"mono", "number"}:
            needs.add("mono")
        return frozenset(needs)


def _plate_block(b: Builder, block: Mapping[str, Any]) -> str:
    return plates.plate(
        b,
        str(block["art"]),
        block.get("caption", ""),
        str(block.get("width", "wide")),
        block.get("spots"),
        block.get("notes"),
    )


def _drawings(story: Mapping[str, Any], path: Path, facts: Any) -> dict[str, Drawing]:
    """Each painting's drawing, read; drawings that fail to read report elsewhere."""
    found: dict[str, Drawing] = {}
    for key, text in art.drawings(story, path.parent, facts, Report()).items():
        try:
            found[key] = parse(text)
        except SvgError:
            continue
    return found


def _check(story: Mapping[str, Any], facts: Any, path: Path, report: Report) -> None:
    """chronicle's block checks, with the anchors, layers and rigs its drawings define."""
    drawn = _drawings(story, path, facts)
    anchors = {key: set(drawing.anchors) for key, drawing in drawn.items()}
    checks.notes(story, anchors, report)
    game.check(story, report)
    rooms.check(story, anchors, report)
    panorama.check(story, drawn, report)
    tour.check(story, anchors, report)


# -------------------------------------------------------------------- policy
def distinct(spec: Mapping[str, Any] | None, story_path: Path) -> list[str]:
    """The sameness review against the bundled examples and sibling run folders."""
    return review.review(spec, other_themes(story_path))


def other_themes(story_path: Path) -> dict[str, Any]:
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


# --------------------------------------------------------------------- scene
def _scene_check(
    anim: Mapping[str, Any], facts: Mapping[str, Any], sources: Sources, report: Report
) -> None:
    anchors: set[str] | None = None
    layers: set[str] | None = None
    if sources.drawing:
        try:
            drawing = parse(sources.drawing)
        except SvgError as exc:
            report.errors.append(f"scene.art: {exc}")
        else:
            anchors = set(drawing.anchors)
            layers = {layer.name for layer in drawing.layers}
    scene.check(anim["scene"], anim.get("steps", []), anchors, layers, facts, report)


def _scene_prepare(anim: Mapping[str, Any], facts: Mapping[str, Any]) -> Prepared:
    return Prepared(anim, diagram_kind.floor)


def _scene_figure(
    anim: Mapping[str, Any],
    prepared: Prepared,
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    sources: Sources,
    words: Callable[[str], str],
) -> tuple[str, list[str]]:
    if sources.painting is None:
        raise ValueError("a scene animation needs its painting; paint it first")
    return scene.figure(anim["scene"], sources.painting, sources.images, plan, box, timeline, words)


def _scene_drawing(body: Mapping[str, Any]) -> str:
    return str(body["art"].get("svg", "")) if isinstance(body.get("art"), Mapping) else ""


def _scene_sources(
    anim: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], out: Path, force: bool
) -> Sources:
    return _painted(anim["scene"]["art"], folder, facts, out, force)


def _painted(
    spec: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], out: Path, force: bool
) -> Sources:
    """Paint an animation's art (once; unchanged art is kept) and embed its images."""
    story = {"art": {"scene": spec}}
    report = Report()
    texts = art.drawings(story, folder, facts, report)
    if not report.ok:
        raise ValueError("; ".join(report.errors))
    art.paint(story, texts, out, 1.0, force)
    entry = store.read_json(out / art.ART_DIR / art.MANIFEST)["scene"]
    files = [str(entry["file"]), *(str(layer["file"]) for layer in entry.get("layers", []))]
    images = {f: store.data_uri(out / f) for f in files}
    return Sources(drawing=texts.get("scene", ""), painting=entry, images=images)


SCENE = Kind(
    skeleton={"art": {"svg": "drawing.svg", "seed": 1, "alt": ""}, "spots": []},
    next_step="draw drawing.svg as a story plate, with a data-anchor for each spot",
    check=_scene_check,
    prepare=_scene_prepare,
    figure=_scene_figure,
    drawing=_scene_drawing,
    build_sources=_scene_sources,
)


# ----------------------------------------------------------------------- rig
def _rig_check(
    anim: Mapping[str, Any], facts: Mapping[str, Any], sources: Sources, report: Report
) -> None:
    """A rig animation plays a drawing's rigs; its gait may replace the drawing's own."""
    body = anim["rig"]
    for key in sorted(set(body) - {"art", "gait"}):
        report.errors.append(f"rig.{key} is unknown; a rig takes art and gait")
    if not isinstance(body.get("art"), Mapping) or not body["art"].get("svg"):
        report.errors.append("rig.art needs an svg: a drawing with a data-rig group of parts")
    if body.get("gait") is not None and body["gait"] not in GAITS:
        report.errors.append(f"rig.gait must be one of {', '.join(GAITS)}")
    if sources.drawing:
        try:
            if not parse(sources.drawing).rigs:
                report.errors.append("rig.art draws no data-rig group to move")
        except SvgError as exc:
            report.errors.append(f"rig.art: {exc}")
    for i, step in enumerate(anim.get("steps", [])):
        acts = sorted(set(step) & set(ACTIONS)) if isinstance(step, Mapping) else []
        if acts:
            report.errors.append(
                f"steps[{i}]: a rig animation's steps take captions, not {acts[0]}"
            )


def _rig_figure(
    anim: Mapping[str, Any],
    prepared: Prepared,
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    sources: Sources,
    words: Callable[[str], str],
) -> tuple[str, list[str]]:
    if sources.painting is None:
        raise ValueError("a rig animation needs its painting; paint it first")
    body = anim["rig"]
    painting = dict(sources.painting)
    if body.get("gait"):
        rigs = dict(painting.get("rigs", {}))
        painting["rigs"] = {name: {**rig, "gait": body["gait"]} for name, rig in rigs.items()}
    still = {"art": body["art"], "develop": False, "spots": []}
    return scene.figure(still, painting, sources.images, plan, box, timeline, words)


def _rig_sources(
    anim: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], out: Path, force: bool
) -> Sources:
    return _painted(anim["rig"]["art"], folder, facts, out, force)


RIG = Kind(
    skeleton={"art": {"svg": "drawing.svg", "seed": 1, "alt": ""}, "gait": "walk"},
    next_step=(
        "draw drawing.svg with a data-rig group whose data-part groups each turn about a "
        "data-pivot (references/illustration.md, Rigs)"
    ),
    check=_rig_check,
    prepare=_scene_prepare,
    figure=_rig_figure,
    drawing=_scene_drawing,
    build_sources=_rig_sources,
)


# ---------------------------------------------------------------- register
registry.set_art(Painter())
registry.add_block(
    "plate", ("art",), ("caption", "spots", "width", "notes"), _plate_block, after="table"
)
# Chapter and hero art are plates too, so these parts follow every painted image.
registry.add_parts(by_type={"plate": ("js/30-plates.js", "css/11-plates.css", "css/40-drawn.css")})
# Pen notes and figures in parts ship only on pages whose plates have them.
registry.add_parts(
    by_type={
        "notes": ("js/31-notes.js", "css/16-notes.css"),
        "rig": ("js/33-rigs.js", "css/15-rigs.css"),
    }
)
# Places to explore: a wide habitat with animals, rooms through doorways, a map tour.
registry.add_block(
    "panorama",
    ("art",),
    (
        "title",
        "subtitle",
        "label",
        "intro",
        "view",
        "animals",
        "zones",
        "tide",
        "front",
        "journal",
        "source",
    ),
    panorama.panorama,
    after="plate",
)
registry.add_block(
    "rooms", ("rooms",), ("title", "subtitle", "source"), rooms.rooms, after="panorama"
)
registry.add_block(
    "tour",
    ("art", "stops"),
    ("title", "subtitle", "hint", "pins", "key", "source"),
    tour.tour,
    after="rooms",
)
registry.add_parts(
    by_type={
        "panorama": ("js/33-rigs.js", "js/34-panorama.js", "css/17-panorama.css"),
        "rooms": ("js/35-rooms.js", "css/18-rooms.css"),
        "tour": ("js/36-tour.js", "css/19-tour.css"),
    }
)
# A story with a `game` plays its quizzes as holes; the scorecard totals the round.
_QUIZ_REQUIRED, _QUIZ_OPTIONAL = model.BLOCKS["quiz"]
registry.add_block(
    "quiz", _QUIZ_REQUIRED, (*_QUIZ_OPTIONAL, "par", "id"), game.quiz, after="diagram"
)
registry.add_block(
    "scorecard", (), ("title", "subtitle", "id", "source"), game.scorecard, after="quiz"
)
registry.add_parts(
    by_type={
        "hole": ("js/32-game.js", "css/12-game.css"),
        "scorecard": ("js/32-game.js", "css/12-game.css"),
    }
)
chrome.register()
registry.add_kind("scene", SCENE, first=True)
registry.add_kind("rig", RIG)
registry.POLICIES["distinct"] = distinct
registry.CHECKS["chronicle"] = _check
registry.COMMANDS["motifs"] = registry.Command(commands.motifs_parser, commands.motifs)
registry.COMMANDS["research"] = registry.Command(commands.research_parser, commands.research)
registry.COMMANDS["widgets"] = registry.Command(widgets.parser, widgets.run)
registry.add_asset_root(resources.files("chronicle.assets"))
registry.DEFAULTS.prog = "chronicle"
registry.DEFAULTS.policy = "distinct"
registry.DEFAULTS.kind = "scene"
registry.DEFAULTS.new_folders = (art.ART_DIR, "diagrams", "widgets")
registry.DEFAULTS.new_next = (
    "do the design pass (references/identity.md), then fill theme.concept first"
)
