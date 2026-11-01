"""Every file the plugin reads or writes goes through here: JSON in, HTML and images out."""

from __future__ import annotations

import base64
import json
from importlib import resources
from importlib.resources.abc import Traversable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from chronicle_engine import registry

if TYPE_CHECKING:
    import numpy as np
    import numpy.typing as npt


class StoreError(OSError):
    """A file that could not be read or written, with the path in the message."""


def read_json(path: Path) -> Any:
    """Parse a JSON file; errors name the file, line and column."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot read {path}: {exc.strerror}") from exc
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StoreError(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON, {exc.msg}") from exc


def read_text(path: Path) -> str:
    """Read a UTF-8 text file such as an SVG drawing or a widget script."""
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot read {path}: {exc.strerror}") from exc


def read_bytes(path: Path) -> bytes:
    """Read a binary file such as a deck to upload."""
    try:
        return path.read_bytes()
    except OSError as exc:
        raise StoreError(f"cannot read {path}: {exc.strerror}") from exc


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot write {path}: {exc.strerror}") from exc


def write_bytes(path: Path, data: bytes) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError as exc:
        raise StoreError(f"cannot write {path}: {exc.strerror}") from exc


def _roots() -> list[Traversable]:
    """The engine's asset folder, then each folder a plugin registered."""
    return [resources.files("chronicle_engine.assets"), *registry.ASSET_ROOTS]


def asset(name: str) -> str:
    """Read a bundled runtime file (stylesheet, script or data) from the first root that has it."""
    for root in _roots():
        path = root.joinpath(name)
        if path.is_file():
            return path.read_text(encoding="utf-8")
    raise StoreError(f"no bundled file {name}")


def asset_parts(folder: str, suffix: str) -> str:
    """Join every bundled file in `folder` ending in `suffix`, across roots, in name order."""
    found: dict[str, Traversable] = {}
    for root in _roots():
        base = root.joinpath(folder)
        if not base.is_dir():
            continue
        for entry in base.iterdir():
            if entry.name.endswith(suffix):
                found.setdefault(entry.name, entry)
    return "\n".join(found[name].read_text(encoding="utf-8") for name in sorted(found))


def asset_files(names: list[str]) -> dict[str, str]:
    """Read each named bundled file, such as the page parts, by its name."""
    return {name: asset(name) for name in names}


def fonts() -> Any:
    """The font list a theme may pick from."""
    return json.loads(asset("fonts.json"))


def write_webp(path: Path, image: npt.NDArray[np.uint8], quality: int = 82) -> int:
    """Encode an 8-bit BGR image as WebP; returns the byte size written."""
    import cv2  # imported here so text-only commands run without OpenCV installed

    ok, buffer = cv2.imencode(".webp", image, [cv2.IMWRITE_WEBP_QUALITY, quality])
    if not ok:
        raise StoreError(f"could not encode {path} as WebP")
    data = buffer.tobytes()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    except OSError as exc:
        raise StoreError(f"cannot write {path}: {exc.strerror}") from exc
    return len(data)


def data_uri(path: Path) -> str:
    """A file as a data: URI, for single-file pages."""
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise StoreError(f"cannot read {path}: {exc.strerror}") from exc
    kind = "image/webp" if path.suffix == ".webp" else "image/png"
    return f"data:{kind};base64,{base64.b64encode(raw).decode('ascii')}"


def decode_png(data: bytes) -> npt.NDArray[np.uint8]:
    """PNG bytes, such as a browser screenshot, as an 8-bit BGR image."""
    import cv2  # imported here so text-only commands run without OpenCV installed
    import numpy as np

    image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise StoreError("a captured frame is not a readable PNG")
    return np.asarray(image, np.uint8)


def write_png(path: Path, image: npt.NDArray[np.uint8]) -> int:
    """Encode an 8-bit BGR image as PNG; returns the byte size written."""
    import cv2  # imported here so text-only commands run without OpenCV installed

    ok, buffer = cv2.imencode(".png", image, [cv2.IMWRITE_PNG_COMPRESSION, 6])
    if not ok:
        raise StoreError(f"could not encode {path} as PNG")
    data = buffer.tobytes()
    write_bytes(path, data)
    return len(data)
