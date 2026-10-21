"""The port every metrics source implements; `core` never imports a connector."""

from __future__ import annotations

from typing import Protocol

from perf_ratchet.core.model import Journey, Series, Window


class SeriesSource(Protocol):
    def fetch(self, journey: Journey, window: Window) -> Series:
        """Daily values for one journey over the window, in the journey's unit."""
        ...
