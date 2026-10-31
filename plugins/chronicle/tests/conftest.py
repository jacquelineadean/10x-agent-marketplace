"""Shared fixtures: the Keystone example story and facts that ship with the plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import chronicle.pack  # noqa: F401  (registers chronicle's blocks, art, kinds and commands)
import pytest
from chronicle_engine import registry
from chronicle_engine.connectors.files import store
from chronicle_engine.core.story import derive
from chronicle_engine.core.story.render import Assets

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "keystone"


@pytest.fixture
def story() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLE / "story.json").read_text(encoding="utf-8"))
    return data


@pytest.fixture
def raw_facts() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLE / "facts.json").read_text(encoding="utf-8"))
    return data


@pytest.fixture
def facts(raw_facts: dict[str, Any]) -> dict[str, Any]:
    return derive.apply(raw_facts)


@pytest.fixture
def example_dir() -> Path:
    return EXAMPLE


@pytest.fixture
def assets() -> Assets:
    """A one-line stub for each runtime part, the real font list, and the example's files."""
    files = {"diagrams/jam.svg": (EXAMPLE / "diagrams" / "jam.svg").read_text(encoding="utf-8")}
    parts = {name: f"/* {name} */" for name in registry.all_parts()}
    return Assets(parts=parts, fonts=json.loads(store.asset("fonts.json")), files=files)
