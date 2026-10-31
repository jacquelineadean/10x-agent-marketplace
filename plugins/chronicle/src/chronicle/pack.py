"""chronicle's registrations with the engine.

Plates, the painter, the page chrome, scenes, TADs, the sameness review and the `motifs`
command.

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
from chronicle_engine.core.motion.model import Plan
from chronicle_engine.core.motion.timeline import Timeline
from chronicle_engine.core.story.model import Report
from chronicle_engine.core.story.render import Builder
from chronicle_engine.registry import Kind, Prepared, Sources

from chronicle.core.motion import scene
from chronicle.core.motion.tad import draw as tad_draw
from chronicle.core.motion.tad import spec as tad_spec
from chronicle.core.motion.tad.spec import Tad
from chronicle.core.story import chrome, plates, review
from chronicle.entrypoints.cli import art, commands

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
    return b.art(
        str(block["art"]),
        block.get("caption", ""),
        str(block.get("width", "wide")),
        block.get("spots"),
    )


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
    from chronicle.core.watercolor.svg.parse import SvgError, parse

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
    """Paint the scene's art (once; unchanged art is kept) and embed its images."""
    story = {"art": {"scene": anim["scene"]["art"]}}
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


# ----------------------------------------------------------------------- tad
def _tad_check(
    anim: Mapping[str, Any], facts: Mapping[str, Any], sources: Sources, report: Report
) -> None:
    tad = tad_spec.read(anim["tad"], report, facts)
    if tad is not None:
        tad_draw.check_steps(anim.get("steps", []), tad, report)


def _tad_prepare(anim: Mapping[str, Any], facts: Mapping[str, Any]) -> Prepared:
    found = Report()
    tad = tad_spec.read(anim["tad"], found, facts)
    if tad is None or found.errors:
        raise ValueError("; ".join(found.errors) or "the tad object is invalid")
    if not anim.get("steps"):
        anim = {**anim, "steps": tad_draw.default_steps(tad)}
    return Prepared(anim, _tad_floor(tad), lambda plan: tad_draw.captions(plan, tad), tad)


def _tad_floor(tad: Tad) -> Callable[[Mapping[str, Any]], float]:
    return lambda raw: tad_draw.floor(raw, tad)


def _tad_figure(
    anim: Mapping[str, Any],
    prepared: Prepared,
    plan: Plan,
    box: stage.Box,
    timeline: Timeline,
    sources: Sources,
    words: Callable[[str], str],
) -> tuple[str, list[str]]:
    tad: Tad = prepared.state
    return tad_draw.figure(tad, plan, box, timeline)


TAD = Kind(
    skeleton={
        "direction": "right",
        "groups": [],
        "nodes": [{"id": "client", "label": "Client", "kind": "client"}],
        "edges": [],
        "flows": [],
    },
    next_step="write the nodes, groups, edges and flows",
    check=_tad_check,
    prepare=_tad_prepare,
    figure=_tad_figure,
)


# ---------------------------------------------------------------- register
registry.set_art(Painter())
registry.add_block("plate", ("art",), ("caption", "spots", "width"), _plate_block, after="table")
# Chapter and hero art are plates too, so these parts follow every painted image.
registry.add_parts(by_type={"plate": ("js/30-plates.js", "css/11-plates.css", "css/40-drawn.css")})
chrome.register()
registry.add_kind("scene", SCENE, first=True)
registry.add_kind("tad", TAD)
registry.POLICIES["distinct"] = distinct
registry.COMMANDS["motifs"] = registry.Command(commands.motifs_parser, commands.motifs)
registry.add_asset_root(resources.files("chronicle.assets"))
registry.DEFAULTS.prog = "chronicle"
registry.DEFAULTS.policy = "distinct"
registry.DEFAULTS.kind = "tad"
registry.DEFAULTS.new_folders = (art.ART_DIR, "diagrams", "widgets")
registry.DEFAULTS.new_next = (
    "do the design pass (references/identity.md), then fill theme.concept first"
)
