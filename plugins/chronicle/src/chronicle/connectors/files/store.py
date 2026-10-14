"""Every file the plugin reads or writes goes through here: JSON in, HTML and images out."""

from __future__ import annotations

import base64
import json
from importlib import resources
from pathlib import Path
from typing import TYPE_CHECKING, Any

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


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot write {path}: {exc.strerror}") from exc


def asset(name: str) -> str:
    """Read a bundled runtime file (stylesheet or script)."""
    return resources.files("chronicle.assets").joinpath(name).read_text(encoding="utf-8")


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
