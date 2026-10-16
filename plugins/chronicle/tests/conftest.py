"""Shared fixtures: the Keystone example story and facts that ship with the plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from chronicle.connectors.files import store
from chronicle.core.story import derive
from chronicle.core.story.render import Assets

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
    """Stub runtime, the real font list, and the files the example's blocks name."""
    files = {"diagrams/jam.svg": (EXAMPLE / "diagrams" / "jam.svg").read_text(encoding="utf-8")}
    return Assets(
        css="/* css */", js="/* js */", fonts=json.loads(store.asset("fonts.json")), files=files
    )
