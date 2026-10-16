"""Scenes: what to paint, as data.

A scene is either a preset (a composed illustration with optional moving layers) or a
list of motif calls that Claude writes for a subject no preset covers:

    {"size": [1600, 700], "seed": 4, "vignette": "deckle",
     "elements": [{"motif": "sky", "horizon": 460, "mood": "dawn"},
                  {"motif": "mountains", "base": 470, "height": 150}],
     "layers": [{"name": "rain", "motion": "fall",
                 "elements": [{"motif": "rain", "count": 300}]}]}
"""

from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from functools import partial
from typing import Any

import numpy as np
import numpy.typing as npt

from chronicle.core.watercolor.canvas import Canvas
from chronicle.core.watercolor.motifs import nature, structures

Image = npt.NDArray[np.uint8]
MOTIONS = ("none", "descend", "drift", "fall", "cross", "rise", "sway", "bob", "pop", "spin")
VIGNETTES = ("deckle", "soft", "spot", "none")


@dataclass
class Layer:
    """A separately painted piece that the page moves; `box` is (x, y, w, h) in scene px."""

    name: str
    image: Image
    box: tuple[int, int, int, int]
    motion: str = "none"
    travel: float = 0.0
    blend: str = "multiply"


@dataclass
class Painting:
    """One finished illustration: a base sheet, moving layers and named points of interest."""

    width: int
    height: int
    base: Image
    layers: list[Layer] = field(default_factory=list)
    anchors: dict[str, tuple[float, float]] = field(default_factory=dict)
    labels: list[dict[str, Any]] = field(default_factory=list)


MotifFn = Callable[..., Any]

MOTIFS: dict[str, MotifFn] = {
    "sky": nature.sky,
    "sun": nature.sun,
    "mountains": nature.mountains,
    "hills": nature.hills,
    "treeline": nature.treeline,
    "tree": nature.tree,
    "grass": nature.grass,
    "bank": nature.bank,
    "water": nature.water,
    "rain": nature.rain,
    "birds": nature.birds,
    "arch_bridge": structures.arch_bridge,
    "trestle": structures.trestle,
    "crane": structures.crane,
    "road": structures.road,
    "milestone": structures.milestone,
    "buildings": structures.buildings,
    "vehicle": structures.vehicle,
    "figure": structures.figure,
}

# Primitive brush calls on the canvas itself, for shapes no motif covers.
PRIMITIVES = ("wash", "ink", "pencil", "glow", "reserve", "drybrush", "splatter", "reflect")


class SceneError(ValueError):
    """A scene spec that cannot be painted, with a message that says what to change."""


def motif_names() -> list[str]:
    """Every name a scene element may use, motifs first."""
    return [*MOTIFS, *PRIMITIVES]


def motif_signature(name: str) -> str:
    """Human-readable parameter list for one motif or primitive, for docs and errors."""
    fn: Callable[..., Any] = MOTIFS[name] if name in MOTIFS else getattr(Canvas, name)
    params = list(inspect.signature(fn).parameters.values())[1:]
    return ", ".join(str(p) for p in params)


def run_element(c: Canvas, element: Mapping[str, Any]) -> Any:
    """Paint one element: {"motif": name, ...params}."""
    if "motif" not in element:
        raise SceneError(f"element {dict(element)!r} needs a 'motif' key")
    name = str(element["motif"])
    params = {k: v for k, v in element.items() if k != "motif"}
    if name in MOTIFS:
        target: Callable[..., Any] = MOTIFS[name]
        bound: Callable[..., Any] = partial(target, c)
    elif name in PRIMITIVES:
        bound = getattr(c, name)
        target = getattr(Canvas, name)
    else:
        raise SceneError(f"unknown motif {name!r}; use one of: {', '.join(motif_names())}")
    allowed = set(list(inspect.signature(target).parameters)[1:])
    unknown = sorted(set(params) - allowed)
    if unknown:
        raise SceneError(
            f"motif {name!r} has no parameter {', '.join(unknown)}; "
            f"it takes ({motif_signature(name)})"
        )
    try:
        return bound(**params)
    except (TypeError, ValueError) as exc:
        raise SceneError(f"motif {name!r} failed: {exc}") from exc


def paint_elements(spec: Mapping[str, Any], scale: float = 1.0) -> Painting:
    """Paint a scene written as element lists."""
    width, height = _size(spec)
    seed = int(spec.get("seed", 1))
    vignette = str(spec.get("vignette", "deckle"))
    if vignette not in VIGNETTES:
        raise SceneError(f"unknown vignette {vignette!r}; use one of {', '.join(VIGNETTES)}")
    canvas = Canvas(width, height, seed=seed, scale=scale)
    for element in spec.get("elements", []):
        run_element(canvas, element)
    painting = Painting(width, height, canvas.finish(vignette))
    for k, layer_spec in enumerate(spec.get("layers", [])):
        motion = str(layer_spec.get("motion", "none"))
        if motion not in MOTIONS:
            raise SceneError(f"unknown motion {motion!r}; use one of {', '.join(MOTIONS)}")
        layer_canvas = Canvas(width, height, seed=seed + 101 + k, scale=scale, paper=canvas.paper)
        for element in layer_spec.get("elements", []):
            run_element(layer_canvas, element)
        image, box = layer_canvas.sprite()
        if box is not None:
            painting.layers.append(
                Layer(
                    name=str(layer_spec.get("name", f"layer{k}")),
                    image=image,
                    box=box,
                    motion=motion,
                    travel=float(layer_spec.get("travel", 0.0)),
                )
            )
    for name, point in dict(spec.get("anchors", {})).items():
        painting.anchors[str(name)] = (float(point[0]), float(point[1]))
    return painting


def _size(spec: Mapping[str, Any]) -> tuple[int, int]:
    size = spec.get("size", [1600, 800])
    try:
        width, height = int(size[0]), int(size[1])
    except (TypeError, ValueError, IndexError) as exc:
        raise SceneError(f"size must be [width, height], got {size!r}") from exc
    if not (200 <= width <= 3200 and 120 <= height <= 3200):
        raise SceneError(f"size {width}x{height} is outside 200x120 to 3200x3200")
    return width, height
