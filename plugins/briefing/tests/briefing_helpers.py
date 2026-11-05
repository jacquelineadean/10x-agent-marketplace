"""Run briefing in its own process, so its registrations never meet chronicle's in a test."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
EXAMPLES = PLUGIN / "examples"
TODAY = "2026-10-31"


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """`python -m briefing` with the plugin's own src folder, as its launcher runs it."""
    merged = {**os.environ, "PYTHONPATH": str(PLUGIN / "src"), **(env or {})}
    return subprocess.run(  # noqa: S603 - fixed interpreter and arguments the test builds
        [sys.executable, "-m", "briefing", *args],
        capture_output=True,
        text=True,
        env=merged,
        check=False,
        timeout=180,
    )
