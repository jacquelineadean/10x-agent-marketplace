"""The sources plugin's files: a recipe per system, a user-run connect skill, a short gatherer."""

from __future__ import annotations

import json
from pathlib import Path

from sources.core.systems import SYSTEMS

PLUGIN = Path(__file__).resolve().parents[1]
PLUGINS = PLUGIN.parent


def _frontmatter(path: Path) -> dict[str, str]:
    lines = path.read_text(encoding="utf-8").split("---\n")[1].splitlines()
    return {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in lines) if v}


def test_every_system_has_a_recipe_with_the_sections_the_gatherer_reads() -> None:
    for system in SYSTEMS:
        text = (PLUGIN / "recipes" / f"{system.id}.md").read_text(encoding="utf-8")
        for heading in ("## Reach", "## Facts", "## queries.json"):
            assert heading in text, (system.id, heading)
        assert "## Never" in text or "## SQL" in text, system.id
    assert len(list((PLUGIN / "recipes").glob("*.md"))) == len(SYSTEMS)


def test_connect_is_run_only_by_the_user() -> None:
    meta = _frontmatter(PLUGIN / "skills" / "connect" / "SKILL.md")
    assert meta["name"] == "connect"
    assert meta["disable-model-invocation"] == "true"


def test_the_gatherer_description_stays_short() -> None:
    meta = _frontmatter(PLUGIN / "agents" / "gatherer.md")
    assert meta["name"] == "gatherer"
    assert len(meta["description"]) <= 450  # about 90 tokens in every session's listing


def test_the_facts_reference_links_the_engines() -> None:
    link = PLUGIN / "references" / "facts.md"
    engine = PLUGINS.parent / "packages" / "chronicle-engine" / "src" / "chronicle_engine"
    assert link.is_symlink()
    assert link.resolve() == (engine / "references" / "facts.md").resolve()


def test_no_plugin_bundles_an_mcp_server() -> None:
    for manifest in PLUGINS.glob("*/.claude-plugin/plugin.json"):
        assert "mcpServers" not in json.loads(manifest.read_text(encoding="utf-8")), manifest
    assert list(PLUGINS.glob("*/.mcp.json")) == []
