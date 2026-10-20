"""Run folders: where a story's or an animation's files go, kept out of git."""

from __future__ import annotations

from pathlib import Path

from chronicle.connectors.files import store


def ignore(folder: Path) -> str:
    """Add the run folder's top folder to the repository's .gitignore when it is missing."""
    cwd = Path.cwd()
    try:
        top = folder.resolve().relative_to(cwd).parts[0]
    except (ValueError, IndexError):
        return ""
    if not (cwd / ".git").exists():
        return ""
    path = cwd / ".gitignore"
    text = store.read_text(path) if path.exists() else ""
    entry = f"{top}/"
    if entry in text.split() or top in text.split():
        return ""
    store.write_text(path, text + ("" if not text or text.endswith("\n") else "\n") + entry + "\n")
    return entry
