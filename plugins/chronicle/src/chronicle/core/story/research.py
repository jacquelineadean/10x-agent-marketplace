"""Checks on what the researcher writes: facts that say where they came from, and a digest
small enough for the main conversation.

`research/facts.json` keeps every fact under `research`, each record with a `source` and a
`locator` (a page, a timestamp or a URL). `research/material.md` is the digest the story
skill reads in place of the material itself.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from typing import Any

LIMIT = 12_000
SECTIONS = ("Outline", "People", "Places", "Timeline", "Glossary", "Quotes", "Disagreements")


def _records(node: Any, path: str) -> Iterator[tuple[str, Any]]:
    if isinstance(node, Mapping) and "value" not in node:
        for key, child in node.items():
            yield from _records(child, f"{path}.{key}")
    else:
        yield path, node


def check_facts(facts: Any) -> list[str]:
    """Problems in research/facts.json; empty when every fact carries its locator."""
    if not isinstance(facts, Mapping):
        return ["research/facts.json must hold a JSON object"]
    errors = [
        f"research/facts.json key {key!r}: put every fact under 'research'"
        for key in facts
        if key not in ("research", "derive")
    ]
    for path, node in _records(facts.get("research", {}), "research"):
        if isinstance(node, list):
            continue
        if not isinstance(node, Mapping):
            errors.append(f"{path}: write a record with value, source and locator")
            continue
        for key in ("source", "locator"):
            if not str(node.get(key, "")).strip():
                errors.append(f"{path}: needs a {key}")
    return errors


def check_material(text: str) -> list[str]:
    """Problems in research/material.md: over 12,000 bytes, or a section missing."""
    errors = []
    size = len(text.encode("utf-8"))
    if size > LIMIT:
        errors.append(f"research/material.md is {size} bytes; cut it to {LIMIT}")
    headings = {line[3:].strip() for line in text.splitlines() if line.startswith("## ")}
    missing = [s for s in SECTIONS if s not in headings]
    if missing:
        errors.append(f"research/material.md lacks sections: {', '.join(missing)}")
    return errors
