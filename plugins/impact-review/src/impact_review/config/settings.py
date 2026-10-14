"""The only module that reads environment variables. `.env` never overrides a set variable."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

TOKEN_NAMES = ("GITHUB_TOKEN", "GH_TOKEN")
HOST_NAME = "IMPACT_REVIEW_HOST"
RUNS_NAME = "IMPACT_REVIEW_RUNS"
DEFAULT_HOST = "github.com"
DEFAULT_RUNS_FOLDER = "~/impact-review-runs"


@dataclass(frozen=True)
class Settings:
    host: str
    runs_root: Path


def read_dotenv(path: Path) -> dict[str, str]:
    """KEY=VALUE lines; blank lines and `#` comments skipped; matching quotes stripped."""
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key.strip()] = value
    return values


def load_environment(
    environ: Mapping[str, str] | None = None, dotenv: Path = Path(".env")
) -> dict[str, str]:
    """Process environment first; `.env` only fills names that are not already set."""
    merged = dict(os.environ if environ is None else environ)
    for key, value in read_dotenv(dotenv).items():
        merged.setdefault(key, value)
    return merged


def settings_from(env: Mapping[str, str]) -> Settings:
    return Settings(
        host=env.get(HOST_NAME, DEFAULT_HOST),
        runs_root=Path(env.get(RUNS_NAME, DEFAULT_RUNS_FOLDER)).expanduser(),
    )
