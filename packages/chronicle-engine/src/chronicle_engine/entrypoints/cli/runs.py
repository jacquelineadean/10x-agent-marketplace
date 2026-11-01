"""Run folders: where a story's or an animation's files go, kept out of git."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from chronicle_engine.config import settings
from chronicle_engine.connectors.files import store
from chronicle_engine.core.story import brand, derive
from chronicle_engine.core.story.facts import attach_queries, merge


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
    facts = merge(named)
    queries = path.parent / "queries.json"
    if default_required and queries.is_file():
        data = store.read_json(queries)
        entries = data.get("queries", {}) if isinstance(data, Mapping) else {}
        refreshed = str(data.get("refreshed", "")) if isinstance(data, Mapping) else ""
        facts = attach_queries(
            facts,
            {str(k): v for k, v in entries.items() if isinstance(v, Mapping)},
            refreshed,
        )
    return derive.apply(facts)


def refresh_state(story_path: Path) -> dict[str, Any]:
    """After a refresh, its date and each system still as of an earlier day, oldest first.

    Reads `queries.json` beside the story; empty when there is none or it was never
    refreshed. A layout shows it beside its as-of date.
    """
    path = story_path.parent / "queries.json"
    data = store.read_json(path) if path.is_file() else {}
    refreshed = str(data.get("refreshed", "")) if isinstance(data, Mapping) else ""
    if not refreshed:
        return {}
    oldest: dict[str, str] = {}
    for entry in (data.get("queries") or {}).values():
        if isinstance(entry, Mapping) and str(entry.get("as_of", "")) < refreshed:
            system, when = str(entry.get("system", "")), str(entry.get("as_of", ""))
            if system and when:
                oldest[system] = min(when, oldest.get(system, when))
    stale = [{"system": s, "as_of": d} for s, d in sorted(oldest.items(), key=lambda i: i[1])]
    return {"refreshed": refreshed, "stale": stale}


def brand_kit(choice: str, folder: Path) -> dict[str, Any] | None:
    """The brand kit `--brand` names: run (the default), repo, config or a path.

    `run` reads `brand.json` in the run folder and is optional; the others must exist.
    """
    if choice == "run":
        path = folder / "brand.json"
        return brand.check_kit(store.read_json(path)) if path.is_file() else None
    if choice == "repo":
        root = next(
            (p for p in (folder.resolve(), *folder.resolve().parents) if (p / ".git").exists()),
            None,
        )
        if root is None:
            raise store.StoreError(f"--brand repo: {folder} is not inside a git repository")
        path = root / ".brand" / "brand.json"
    elif choice == "config":
        path = settings.brand_config_path()
    else:
        path = Path(choice)
    if not path.is_file():
        raise store.StoreError(f"no brand kit at {path}")
    return brand.check_kit(store.read_json(path))
