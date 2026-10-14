"""Raw response cache in the run folder: a rerun makes no repeat API calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class RawCache:
    def __init__(self, folder: Path, refresh: bool = False) -> None:
        self.folder = folder
        self.refresh = refresh
        self.hits = 0
        folder.mkdir(parents=True, exist_ok=True)

    def path_for(self, name: str, variables: dict[str, Any]) -> Path:
        digest = hashlib.sha256(json.dumps(variables, sort_keys=True).encode()).hexdigest()[:16]
        return self.folder / f"{name}-{digest}.json"

    def get(self, name: str, variables: dict[str, Any]) -> Any | None:
        path = self.path_for(name, variables)
        if self.refresh or not path.is_file():
            return None
        self.hits += 1
        return json.loads(path.read_text(encoding="utf-8"))

    def put(self, name: str, variables: dict[str, Any], value: Any) -> None:
        self.path_for(name, variables).write_text(json.dumps(value, indent=1), encoding="utf-8")
