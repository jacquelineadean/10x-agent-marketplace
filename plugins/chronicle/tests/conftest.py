"""Shared fixtures: the Keystone example story and facts that ship with the plugin."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from chronicle.core.story import derive

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
