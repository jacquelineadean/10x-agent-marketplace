"""The only module that reads environment variables.

Key values are never kept: `present` reports only which names hold something.
"""

from __future__ import annotations

import os
from collections.abc import Iterable, Mapping
from pathlib import Path

CONNECTIONS_NAME = "SOURCES_CONNECTIONS"


def _env(environ: Mapping[str, str] | None) -> Mapping[str, str]:
    return os.environ if environ is None else environ


def present(names: Iterable[str], environ: Mapping[str, str] | None = None) -> set[str]:
    """The names among `names` that are set to something other than blanks."""
    env = _env(environ)
    return {name for name in names if env.get(name, "").strip()}


def connections_path(environ: Mapping[str, str] | None = None) -> Path:
    """`$SOURCES_CONNECTIONS`, else `$XDG_CONFIG_HOME/sources/connections.json`, else ~/.config."""
    env = _env(environ)
    if env.get(CONNECTIONS_NAME, "").strip():
        return Path(env[CONNECTIONS_NAME]).expanduser()
    base = env.get("XDG_CONFIG_HOME", "").strip()
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "sources" / "connections.json"


def claude_dir(environ: Mapping[str, str] | None = None) -> Path:
    """Claude Code's user folder: `$CLAUDE_CONFIG_DIR`, else ~/.claude."""
    env = _env(environ)
    base = env.get("CLAUDE_CONFIG_DIR", "").strip()
    return Path(base).expanduser() if base else Path.home() / ".claude"
