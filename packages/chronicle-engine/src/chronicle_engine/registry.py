"""Extension points that a plugin fills before a command runs.

The engine names no plugin. A plugin's `pack` module registers its blocks, its art
provider, its page chrome and page parts, its animation kinds, its theme policies, its
commands and its asset folders here; the plugin's `__main__` imports the pack and then
runs the engine's command line. Registration is idempotent by name, so importing a pack
twice changes nothing.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from chronicle_engine.core.motion.model import Plan
    from chronicle_engine.core.motion.stage import Box
    from chronicle_engine.core.motion.timeline import Timeline
    from chronicle_engine.core.story.model import Report
    from chronicle_engine.core.story.render import Builder

Block = Mapping[str, Any]


class ArtProvider(Protocol):
    """Makes the images a story's `art` names, and draws them on the page."""

    missing_dependency: str

    def drawings(
        self, story: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], report: Report
    ) -> dict[str, str]:
        """Read and check the drawings `story.art` names; return each drawing's text."""
        ...

    def make(
        self,
        story: Mapping[str, Any],
        texts: Mapping[str, str],
        out: Path,
        scale: float,
        force: bool,
    ) -> None:
        """Make every image in `story.art` that changed, into `out`."""
        ...

    def manifest(self, out: Path) -> dict[str, Any]:
        """The images made so far, by art key."""
        ...

    def figure(self, b: Builder, key: str, caption: Any, width: str, spots: Any) -> str:
        """One art image as a page figure."""
        ...

    def font_needs(self, manifest: Mapping[str, Any]) -> frozenset[str]:
        """Optional font roles the images' overlay text uses."""
        ...


@dataclass
class Sources:
    """What an animation's entry point read for the figure.

    `drawing` is an SVG the kind plays or paints. `painting` is the art provider's
    manifest entry for an image the kind shows, and `images` maps each of its files to
    the href the SVG embeds.
    """

    drawing: str = ""
    painting: Mapping[str, Any] | None = None
    images: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Prepared:
    """A kind's preparation for planning: the animation to plan and its time floors."""

    anim: Mapping[str, Any]
    floor: Callable[[Mapping[str, Any]], float]
    after_plan: Callable[[Plan], None] | None = None
    state: Any = None


@dataclass(frozen=True)
class Kind:
    """An animation kind: what Claude writes for it and how code draws it.

    `drawing` returns the SVG source the kind's object names (a file or inline markup),
    or "" when it names none. `build_sources` makes what a build needs beyond that, such
    as a painted image. `new_files` are the files `animate new` writes beside the JSON.
    """

    skeleton: Mapping[str, Any]
    next_step: str
    check: Callable[[Mapping[str, Any], Mapping[str, Any], Sources, Report], None]
    prepare: Callable[[Mapping[str, Any], Mapping[str, Any]], Prepared]
    figure: Callable[
        [Mapping[str, Any], Prepared, Plan, Box, Timeline, Sources, Callable[[str], str]],
        tuple[str, list[str]],
    ]
    drawing: Callable[[Mapping[str, Any]], str] | None = None
    build_sources: (
        Callable[[Mapping[str, Any], Path, Mapping[str, Any], Path, bool], Sources] | None
    ) = None
    new_files: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Command:
    """A command a plugin adds to the command line."""

    add_parser: Callable[[Any], None]
    run: Callable[[argparse.Namespace], int]


# Theme policies take the story's theme and the story's path and return warnings.
Policy = Callable[[Mapping[str, Any] | None, Path], list[str]]


@dataclass
class Defaults:
    """Choices a plugin makes for its own pages, animations and run folders."""

    prog: str = "chronicle-engine"
    policy: str = ""
    kind: str = ""
    new_folders: tuple[str, ...] = ("diagrams", "widgets")
    new_next: str = "fill theme.concept, then write the chapters"


@dataclass(frozen=True)
class StatSkin:
    """How a stat panel looks: `paper` prints it on a slip beside the hero's title."""

    paper: bool = False
    fonts: frozenset[str] = frozenset()


@dataclass
class Chrome:
    """The page chrome a theme picks from. The engine brings neutral entries; plugins add more.

    `progress` maps a progress device to whether it needs a drawn path; `lines` are the
    track lines a device may draw; `marks` maps a chapter mark style to its default
    numbering; `frames` maps a frame to its CSS.
    """

    progress: dict[str, bool] = field(default_factory=lambda: {"steps": False})
    lines: list[str] = field(default_factory=lambda: ["solid", "dashed"])
    marks: dict[str, str] = field(
        default_factory=lambda: {
            "label": "decimal",
            "plain": "decimal",
            "step": "decimal",
            "none": "decimal",
        }
    )
    stats: dict[str, StatSkin] = field(
        default_factory=lambda: {"rule": StatSkin(), "cards": StatSkin()}
    )
    frames: dict[str, str] = field(default_factory=lambda: {"none": ""})
    progress_default: str = "steps"
    mark_default: str = "label"


ART: list[ArtProvider] = []
KINDS: dict[str, Kind] = {}
POLICIES: dict[str, Policy] = {}
COMMANDS: dict[str, Command] = {}
ASSET_ROOTS: list[Traversable] = []
DEFAULTS = Defaults()
CHROME = Chrome()
# Page parts, as paths under an asset root. Every page ships ALWAYS; a page with a figure
# of a type also ships PARTS[type]. Parts join in file-name order across roots, so a
# plugin's part can sit between two of the engine's.
ALWAYS: list[str] = [
    "css/00-base.css",
    "css/10-page.css",
    "css/12-page.css",
    "css/14-page.css",
    "css/20-identity.css",
    "js/00-core.js",
    "js/40-progress.js",
    "js/90-boot.js",
]
_CHARTS = ("js/10-charts.js",)
_FIGURES = (*_CHARTS, "js/20-figures.js")
_EXPLAINERS = ("js/50-explainers.js", "css/30-explainers.css")
_LESSONS = (*_CHARTS, "js/60-lessons.js", "css/30-explainers.css")
# The figures js/20-figures.js starts; it draws them with js/10-charts.js.
_FIGURE_TYPES = (
    "stats",
    "scrolly",
    "timeline",
    "stepper",
    "compare",
    "matrix",
    "roadmap",
    "team",
    "model",
)
PARTS: dict[str, tuple[str, ...]] = {
    "chart": _CHARTS,
    **dict.fromkeys(_FIGURE_TYPES, _FIGURES),
    "tilemap": _EXPLAINERS,
    "flow": _EXPLAINERS,
    "diagram": (*_EXPLAINERS, "css/40-drawn.css"),
    **dict.fromkeys(("quiz", "checklist", "widget"), _LESSONS),
}


def set_art(provider: ArtProvider) -> None:
    """Install the one art provider a plugin brings."""
    ART[:] = [provider]


def art() -> ArtProvider | None:
    return ART[0] if ART else None


def add_kind(name: str, kind: Kind, *, first: bool = False) -> None:
    """Register an animation kind; `first` puts it ahead of the kinds already known."""
    rest = {k: v for k, v in KINDS.items() if k != name}
    KINDS.clear()
    if first:
        KINDS[name] = kind
        KINDS.update(rest)
    else:
        KINDS.update(rest)
        KINDS[name] = kind


def add_asset_root(root: Traversable) -> None:
    """Add a package's asset folder; parts from every root join in file-name order."""
    if all(str(r) != str(root) for r in ASSET_ROOTS):
        ASSET_ROOTS.append(root)


def add_block(
    name: str,
    required: tuple[str, ...],
    optional: tuple[str, ...],
    render: Callable[[Builder, Block], str],
    *,
    after: str = "",
) -> None:
    """Register a story block; `after` places it in the list of block types messages show."""
    from chronicle_engine.core.story import dispatch, model

    entries = [(k, v) for k, v in model.BLOCKS.items() if k != name]
    at = next((i + 1 for i, (k, _) in enumerate(entries) if k == after), len(entries))
    entries.insert(at, (name, (required, optional)))
    model.BLOCKS.clear()
    model.BLOCKS.update(entries)
    dispatch.RENDERERS[name] = render


def insert(table: dict[str, Any], entries: Mapping[str, Any], *, before: str = "") -> None:
    """Add entries to an ordered table, ahead of `before` when it is there, else at the end.

    Order matters: theme errors list the choices in this order.
    """
    rest = [(k, v) for k, v in table.items() if k not in entries]
    at = next((i for i, (k, _) in enumerate(rest) if k == before), len(rest))
    rest[at:at] = list(entries.items())
    table.clear()
    table.update(rest)


def add_parts(
    always: tuple[str, ...] = (), by_type: Mapping[str, tuple[str, ...]] | None = None
) -> None:
    """Register page parts: `always` for every page, `by_type` for pages with that figure."""
    for part in always:
        if part not in ALWAYS:
            ALWAYS.append(part)
    for fig, parts in (by_type or {}).items():
        PARTS[fig] = tuple(dict.fromkeys((*PARTS.get(fig, ()), *parts)))


def page_parts(types: Iterable[str]) -> list[str]:
    """The parts a page whose figures have these types ships, in file-name order."""
    names = dict.fromkeys(ALWAYS)
    for fig in types:
        names.update(dict.fromkeys(PARTS.get(fig, ())))
    return sorted(names)


def all_parts() -> list[str]:
    """Every registered part, so a build can read them once."""
    return page_parts(PARTS)
