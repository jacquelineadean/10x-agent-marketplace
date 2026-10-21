"""Pieces the figure kinds share: when a part is on screen, and the packet that travels."""

from __future__ import annotations

from dataclasses import dataclass, field

from chronicle.core.motion.timeline import Point, Timeline, changes, eased
from chronicle.core.story.html import tag


@dataclass
class Life:
    """When a part is on screen: its state at the start and each change after."""

    initial: bool = True
    events: list[tuple[float, bool]] = field(default_factory=list)

    def at(self, t: float) -> bool:
        state = self.initial
        for when, value in self.events:
            if when > t + 1e-9:
                break
            state = value
        return state

    @property
    def moves(self) -> bool:
        return bool(self.events) or not self.initial

    @property
    def shows(self) -> list[float]:
        return [t for t, v in self.events if v]

    @property
    def final(self) -> float:
        return 1.0 if (self.events[-1][1] if self.events else self.initial) else 0.0

    def points(self) -> list[Point]:
        return changes(
            1.0 if self.initial else 0.0, [(t, 1.0 if v else 0.0) for t, v in self.events]
        )


def named(events: dict[str, list[tuple[float, bool]]]) -> dict[str, Life]:
    """Lives of parts that steps show or hide: a part first shown starts hidden."""
    return {x: Life(not ev[0][1], sorted(ev)) for x, ev in events.items() if ev}


def packet(
    pid: str,
    d: str,
    length: float,
    trail: float,
    times: tuple[float, float],
    forward: bool,
    timeline: Timeline,
    unit_length: bool = False,
    **attrs: str | None,
) -> str:
    """A dot with a short trail that runs along path `d` between two times.

    It is the path itself, stroked as one round dot by its dash pattern and moved by the
    dash offset. `length` and `trail` are in the path's dash units: pixels, or shares of
    the path when `unit_length` gives it a pathLength of 1.
    """
    start, end = times
    a, b = (0.0, -length) if forward else (-length, 0.0)
    tail = (trail, trail - length) if forward else (-length, 0.0)
    gap = f"{length * 2 + 60:.4g}"
    out = ""
    for part, dash, (first, last) in (
        ("halo", length * 1e-4, (a, b)),
        ("trail", trail, tail),
        ("dot", length * 1e-4, (a, b)),
    ):
        out += tag(
            "path",
            class_=f"m-{part}",
            id=f"{pid}-{part[0]}",
            d=d,
            pathLength="1" if unit_length else None,
            stroke_dasharray=f"{dash:.4g} {gap}",
            stroke_dashoffset=f"{first:.4g}",
        )
        timeline.add(
            f"#{pid}-{part[0]}", "stroke-dashoffset", eased(start, end, first, last), rest=first
        )
    ramp = min(0.1, (end - start) / 3)
    seen = [(0.0, 0.0), (start - ramp, 0.0), (start, 1.0), (end - ramp, 1.0), (end, 0.0)]
    timeline.add(f"#{pid}", "opacity", seen, rest=0.0)
    return tag("g", out, id=pid, class_="m-packet", **attrs)
