"""The outside world a collector touches: the network, programs and the clock's sleep.

Tests pass recorded replies and fake programs here; nothing else in a collector reaches
outside the process.
"""

from __future__ import annotations

import shutil
import subprocess
import time
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sources.connectors.github.token import gh_cli_token

Runner = Callable[..., subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class Wire:
    opener: Callable[..., Any] = urllib.request.urlopen
    sleeper: Callable[[float], None] = time.sleep
    runner: Runner = subprocess.run
    which: Callable[[str], str | None] = shutil.which
    gh_token: Callable[[str], str | None] = gh_cli_token
    environ: Mapping[str, str] = field(default_factory=dict, repr=False)
