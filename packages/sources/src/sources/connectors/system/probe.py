"""Programs installed on this machine; nothing runs, `PATH` is only searched."""

from __future__ import annotations

import shutil
from collections.abc import Iterable


def installed(programs: Iterable[str]) -> set[str]:
    return {name for name in programs if shutil.which(name)}
