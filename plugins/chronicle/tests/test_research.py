"""The researcher's files: a locator on every fact, and a digest with every section."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from chronicle.core.story import research
from chronicle_engine.entrypoints.cli.main import main

MATERIAL = "\n".join(f"## {name}\nNone.\n" for name in research.SECTIONS)


def test_every_fact_needs_a_source_and_a_locator() -> None:
    facts = {
        "research": {
            "founded": {"value": 1886, "source": "book", "locator": "p. 14"},
            "length": {"value": 11, "unit": "miles", "source": "book"},
            "visits": [3, 4],
            "name": "Ossabaw",
        },
        "github": {},
    }
    assert research.check_facts(facts) == [
        "research/facts.json key 'github': put every fact under 'research'",
        "research.length: needs a locator",
        "research.name: write a record with value, source and locator",
    ]


def test_material_keeps_every_section_under_the_cap() -> None:
    assert research.check_material(MATERIAL) == []
    short = MATERIAL.replace("## Disagreements", "## Notes")
    assert research.check_material(short) == ["research/material.md lacks sections: Disagreements"]
    long = MATERIAL + "x" * research.LIMIT
    assert research.check_material(long)[0].startswith("research/material.md is ")


def test_the_research_command_checks_a_run_folder(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    folder = tmp_path / "research"
    folder.mkdir()
    facts = {"research": {"x": {"value": 1, "source": "notes", "locator": "at 1:02"}}}
    (folder / "facts.json").write_text(json.dumps(facts), encoding="utf-8")
    (folder / "material.md").write_text(MATERIAL, encoding="utf-8")
    assert main(["research", str(tmp_path)]) == 0
    (folder / "material.md").write_text("# Notes\n", encoding="utf-8")
    assert main(["research", str(tmp_path)]) == 1
    assert "lacks sections" in capsys.readouterr().err
