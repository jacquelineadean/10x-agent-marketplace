"""The only module that reads environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path


def brand_config_path(environ: Mapping[str, str] | None = None) -> Path:
    """The user's brand kit: `$XDG_CONFIG_HOME/chronicle/brand.json`, else ~/.config."""
    env = os.environ if environ is None else environ
    base = env.get("XDG_CONFIG_HOME", "").strip()
    root = Path(base).expanduser() if base else Path.home() / ".config"
    return root / "chronicle" / "brand.json"
