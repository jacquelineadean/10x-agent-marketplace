"""Interfaces core needs from the outside; connectors implement them."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from impact_review.core.models import Activity, Profile, Timeframe


class ActivitySource(Protocol):
    def profile(self) -> Profile: ...

    def enable_cache(self, folder: Path, refresh: bool) -> None: ...

    def collect(
        self,
        timeframe: Timeframe,
        profile: Profile,
        orgs: Sequence[str],
        repo_share: bool,
    ) -> Activity: ...
