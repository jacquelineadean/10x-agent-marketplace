"""Run folders: where a story's or an animation's files go, kept out of git."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from chronicle_engine.connectors.files import store
from chronicle_engine.core.story import derive
from chronicle_engine.core.story.facts import merge


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


def load_facts(
    path: Path, doc: Mapping[str, Any], override: Path | None, default_required: bool
) -> Any:
    """The facts a story or animation names, joined and derived.

    `facts_file` names one file or a list beside the document; files join by top-level
    key, as when the researcher's facts sit beside the gatherer's. With no name, the
    document's inline `facts` or `facts.json` beside it is read; an animation may have none.
    """
    if override:
        named = [(str(override), store.read_json(override))]
    elif isinstance(doc.get("facts"), Mapping):
        named = [("facts", doc["facts"])]
    else:
        files = doc.get("facts_file")
        if files is None and not default_required and not (path.parent / "facts.json").exists():
            return derive.apply({})
        names = ["facts.json"] if files is None else [files] if isinstance(files, str) else files
        if not isinstance(names, list) or not names or not all(isinstance(n, str) for n in names):
            raise store.StoreError("facts_file must name a file or a list of files")
        named = [(name, store.read_json(path.parent / name)) for name in names]
    for _, raw in named:
        if not isinstance(raw, Mapping):
            raise store.StoreError("the facts file must hold a JSON object")
    return derive.apply(merge(named))
