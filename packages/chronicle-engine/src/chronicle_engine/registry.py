"""Extension points that a plugin fills before a command runs.

The engine names no plugin. A plugin's `pack` module registers its blocks, its art
provider, its animation kinds, its theme policies, its commands and its asset folders
here; the plugin's `__main__` imports the pack and then runs the engine's command line.
Registration is idempotent by name, so importing a pack twice changes nothing.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping
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


ART: list[ArtProvider] = []
KINDS: dict[str, Kind] = {}
POLICIES: dict[str, Policy] = {}
COMMANDS: dict[str, Command] = {}
ASSET_ROOTS: list[Traversable] = []
DEFAULTS = Defaults()


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
