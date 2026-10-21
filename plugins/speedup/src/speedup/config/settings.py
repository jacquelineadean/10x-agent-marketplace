"""The only module that reads environment variables. `.env` never overrides a set variable."""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

DD_API_KEY = "DD_API_KEY"
DD_APP_KEYS = ("DD_APP_KEY", "DD_APPLICATION_KEY")
DD_SITE = "DD_SITE"
PROMETHEUS_URL = "PROMETHEUS_URL"
PROMETHEUS_TOKEN = "PROMETHEUS_TOKEN"  # noqa: S105  the variable name, not a secret
RUNS_NAME = "SPEEDUP_RUNS"
CONFIG_NAME = "SPEEDUP_CONFIG"
DEFAULT_RUNS_FOLDER = "~/speedup-runs"
DEFAULT_CONFIG = "perf/speedup.json"


@dataclass(frozen=True)
class Settings:
    runs_root: Path
    config: Path
    datadog_site: str
    prometheus_url: str


@dataclass(frozen=True)
class DatadogKeys:
    api_key: str
    app_key: str


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
        value = value.split(" #", 1)[0].strip()
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
        runs_root=Path(env.get(RUNS_NAME) or DEFAULT_RUNS_FOLDER).expanduser(),
        config=Path(env.get(CONFIG_NAME) or DEFAULT_CONFIG),
        datadog_site=env.get(DD_SITE, ""),
        prometheus_url=env.get(PROMETHEUS_URL, ""),
    )


def datadog_keys(env: Mapping[str, str]) -> DatadogKeys:
    api_key = env.get(DD_API_KEY, "").strip()
    app_key = next((env[n].strip() for n in DD_APP_KEYS if env.get(n, "").strip()), "")
    missing = [
        name for name, value in ((DD_API_KEY, api_key), ("DD_APP_KEY", app_key)) if not value
    ]
    if missing:
        raise ValueError(
            f"Datadog needs {' and '.join(missing)} in the environment or .env; or gather with "
            "the Datadog connector in Claude and use `import`"
        )
    return DatadogKeys(api_key, app_key)


def prometheus_token(env: Mapping[str, str]) -> str | None:
    return env.get(PROMETHEUS_TOKEN, "").strip() or None
