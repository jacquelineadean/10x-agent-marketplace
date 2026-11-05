"""The engine's boundary: what it holds, that it imports no plugin, and how plugins link it."""

from __future__ import annotations

import ast
import re
from pathlib import Path

from engine_helpers import ENGINE, ROOT

# Plugin packages the engine must never import; each plugin imports the engine instead.
PLUGIN_PACKAGES = ("chronicle", "briefing", "blueprint", "sources", "impact_review", "speedup")
# Words from one plugin's world. The engine's code, styles and scripts use none of them, so
# a creative or a data feature cannot slip into the shared engine unnoticed.
PLUGIN_WORDS = re.compile(r"\b(watercolou?rs?|plates?|sameness|kpis?|sql|datadog)\b", re.I)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            found.add(node.module)
    return found


def test_engine_modules_exist() -> None:
    expected = [
        "registry.py",
        "core/story/facts.py",
        "core/story/derive.py",
        "core/story/model.py",
        "core/story/render.py",
        "core/story/theme.py",
        "core/story/diagram.py",
        "core/motion/model.py",
        "core/motion/timeline.py",
        "core/motion/stage.py",
        "core/motion/diagram.py",
        "core/motion/render.py",
        "connectors/files/store.py",
        "connectors/browser/shoot.py",
        "connectors/video/encode.py",
        "entrypoints/cli/main.py",
        "entrypoints/cli/animate.py",
    ]
    missing = [name for name in expected if not (ENGINE / name).is_file()]
    assert missing == []


def test_engine_imports_no_plugin() -> None:
    offenders = []
    for path in sorted(ENGINE.rglob("*.py")):
        for module in _imports(path):
            top = module.split(".")[0]
            if top in PLUGIN_PACKAGES:
                offenders.append(f"{path.relative_to(ENGINE)} imports {module}")
    assert offenders == []


def test_chronicle_links_the_engine() -> None:
    link = ROOT / "plugins" / "chronicle" / "src" / "chronicle_engine"
    assert link.is_symlink()
    assert link.resolve() == ENGINE.resolve()


def test_engine_vocabulary() -> None:
    offenders = [
        f"{path.relative_to(ENGINE)}:{n}: {match.group(0)}"
        for path in sorted(ENGINE.rglob("*"))
        if path.is_file() and path.suffix in {".py", ".js", ".css", ".json"}
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        for match in PLUGIN_WORDS.finditer(line)
    ]
    assert offenders == []
