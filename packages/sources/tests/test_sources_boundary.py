"""packages/sources imports neither the chronicle engine nor any plugin."""

from __future__ import annotations

import ast
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[1] / "src" / "sources"
FORBIDDEN = ("chronicle_engine", "chronicle", "briefing", "blueprint", "impact_review", "speedup")


def test_sources_imports_no_engine_or_plugin() -> None:
    offenders = []
    for path in sorted(PACKAGE.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                names = [node.module]
            offenders += [f"{path.name}: {n}" for n in names if n.split(".")[0] in FORBIDDEN]
    assert offenders == []


def test_the_sources_plugin_links_the_package() -> None:
    link = PACKAGE.parents[3] / "plugins" / "sources" / "src" / "sources"
    assert link.is_symlink()
    assert link.resolve() == PACKAGE.resolve()
