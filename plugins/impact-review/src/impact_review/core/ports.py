"""Interfaces core needs from the outside; connectors implement them."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from impact_review.core.models import Activity, Profile, Timeframe
from impact_review.core.scope import Scope, ScopeRequest


class ActivitySource(Protocol):
    def enable_cache(self, folder: Path, refresh: bool) -> None: ...

    def resolve(self, request: ScopeRequest) -> tuple[list[Profile], list[str]]:
        """The people a scope request names, plus the organizations it limits work to."""
        ...

    def collect(
        self,
        timeframe: Timeframe,
        scope: Scope,
        orgs: Sequence[str],
        repo_share: bool,
    ) -> Activity: ...
