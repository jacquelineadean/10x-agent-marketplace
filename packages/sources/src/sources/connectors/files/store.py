"""Every file sources reads or writes: JSON and Markdown in run folders and the config folder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StoreError(OSError):
    """A file that could not be read or written, with the path in the message."""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot read {path}: {exc.strerror}") from exc


def read_json(path: Path) -> Any:
    """Parse a JSON file; errors name the file, line and column."""
    text = read_text(path)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise StoreError(f"{path}:{exc.lineno}:{exc.colno}: invalid JSON, {exc.msg}") from exc


def read_json_or(path: Path, default: Any) -> Any:
    """A JSON file, or `default` when the file does not exist."""
    return read_json(path) if path.is_file() else default


def write_text(path: Path, text: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise StoreError(f"cannot write {path}: {exc.strerror}") from exc


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, indent=1, ensure_ascii=False) + "\n")
