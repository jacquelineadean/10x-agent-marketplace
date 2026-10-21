"""Paint the art a story or an animation names, keeping paintings that did not change.

Shared by the story and animate commands: both write `art/` with a manifest beside the
paintings, and both repaint only a scene whose spec, drawing or painting code changed.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from chronicle.connectors.files import store
from chronicle.core.story import model

ART_DIR = "art"
MANIFEST = "manifest.json"


def drawings(
    story: Mapping[str, Any], folder: Path, facts: Mapping[str, Any], report: model.Report
) -> dict[str, str]:
    """Read and check every scene drawn as SVG, and the fact tokens in its text.

    The parser needs no NumPy, so `check` catches drawing errors before any painting.
    """
    from chronicle.core.watercolor.svg.parse import SvgError, parse

    texts: dict[str, str] = {}
    for key, spec in dict(story.get("art", {})).items():
        if not isinstance(spec, Mapping) or "svg" not in spec:
            continue
        source = str(spec["svg"])
        name = source if len(source) < 80 else "inline svg"
        text = source if source.lstrip().startswith("<svg") else store.read_text(folder / source)
        try:
            drawing = parse(text, int(spec["width"]) if spec.get("width") else None)
        except SvgError as exc:
            report.errors.append(f"art.{key} ({name}): {exc}")
            continue
        for label in drawing.labels:
            model.check_text(label.text, f"art.{key} ({name}) text", "label", facts, report)
        texts[str(key)] = text
    return texts


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


def paint(
    story: Mapping[str, Any], drawings: Mapping[str, str], out: Path, scale: float, force: bool
) -> None:
    from chronicle.core.watercolor import presets, scene  # needs NumPy and OpenCV
    from chronicle.core.watercolor.svg import paint as svg_paint

    art_dir = out / ART_DIR
    manifest_path = art_dir / MANIFEST
    old: dict[str, Any] = {}
    if manifest_path.exists():
        old = store.read_json(manifest_path)
    manifest: dict[str, Any] = {}
    engine = _engine_digest()
    for key, spec in dict(story.get("art", {})).items():
        digest = _scene_hash({**spec, "svg": drawings.get(key, spec.get("svg"))}, scale, engine)
        prior = old.get(key)
        if not force and prior and prior.get("hash") == digest and (out / prior["file"]).exists():
            manifest[key] = prior
            print(f"art: {key} unchanged")
            continue
        try:
            if "preset" in spec:
                painting = presets.paint_preset(str(spec["preset"]), spec.get("params", {}), scale)
            elif key in drawings:
                painting = svg_paint.paint_scene(spec, drawings[key], scale)
            else:
                painting = scene.paint_elements(spec, scale)
        except ValueError as exc:
            raise ValueError(f"art.{key}: {exc}") from exc
        base_rel = f"{ART_DIR}/{key}.webp"
        size = store.write_webp(out / base_rel, painting.base)
        entry: dict[str, Any] = {
            "hash": digest,
            "file": base_rel,
            "width": painting.width,
            "height": painting.height,
            "anchors": {k: [round(v[0], 1), round(v[1], 1)] for k, v in painting.anchors.items()},
            "labels": painting.labels,
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
                    "blend": layer.blend,
                }
            )
        manifest[key] = entry
        print(f"art: {key} painted, {size // 1024} KB")
    store.write_json(manifest_path, manifest)
