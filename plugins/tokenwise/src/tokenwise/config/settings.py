"""The only module that reads environment variables."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

RUNS_NAME = "TOKENWISE_RUNS"
AUTO_APPLY_NAME = "TOKENWISE_AUTO_APPLY"
CONFIG_DIR_NAME = "CLAUDE_CONFIG_DIR"
DEFAULT_RUNS_FOLDER = "~/tokenwise-runs"
DEFAULT_CONFIG_DIR = "~/.claude"


@dataclass(frozen=True)
class Settings:
    runs_root: Path
    claude_dir: Path
    auto_apply: bool


def settings_from(env: Mapping[str, str] | None = None) -> Settings:
    values = os.environ if env is None else env
    return Settings(
        runs_root=Path(values.get(RUNS_NAME) or DEFAULT_RUNS_FOLDER).expanduser(),
        claude_dir=Path(values.get(CONFIG_DIR_NAME) or DEFAULT_CONFIG_DIR).expanduser(),
        auto_apply=values.get(AUTO_APPLY_NAME, "1").strip() not in ("0", "false", "no", "off"),
    )
