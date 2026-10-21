"""The clock of an animation: every moving part is a CSS keyframe track on one loop.

Every track runs for the whole timeline with no delay of its own, so one negative
`animation-delay` seeks the whole figure to any moment. The same file then plays in a
browser and is stepped frame by frame for GIF and video. Only opacity, the dash offset
and the individual transform properties move, because those play in an SVG shown as an
image in every current browser.

A track also has a rest value: what the figure shows where animation is off (reduced
motion, an SVG placed in a slide editor). Rest values are the figure's final state, so a
still copy shows the whole picture.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

TAU = 0.35  # seconds one change of state takes
Value = float | tuple[float, float]
Point = tuple[float, Value]
DEFAULTS: dict[str, Value] = {
    "opacity": 1.0,
    "stroke-dashoffset": 0.0,
    "translate": (0.0, 0.0),
    "rotate": 0.0,
    "scale": 1.0,
}


@dataclass
class Track:
    """The animated properties of one element, found by a CSS selector."""

    selector: str
    props: dict[str, list[Point]] = field(default_factory=dict)
    rest: dict[str, Value] = field(default_factory=dict)
    origin: str = ""
    # Properties whose last value looks the same as their first (a full turn), so the
    # loop restarts without easing back.
    wraps: set[str] = field(default_factory=set)


class Timeline:
    """Tracks on one clock of `duration` seconds that loops or plays once."""

    def __init__(self, duration: float, loop: bool) -> None:
        if duration <= 0:
            raise ValueError("an animation needs a duration above 0 seconds")
        self.duration = duration
        self.loop = loop
        self.tracks: dict[str, Track] = {}

    def add(
        self,
        selector: str,
        prop: str,
        points: Sequence[Point],
        rest: Value | None = None,
        origin: str = "",
        wraps: bool = False,
    ) -> None:
        """Move `prop` of the element through `points` (seconds, value).

        `rest` is the value shown without animation; it defaults to the last value.
        """
        if prop not in DEFAULTS:
            raise ValueError(f"{prop} cannot be animated; use {', '.join(DEFAULTS)}")
        if not points:
            return
        track = self.tracks.setdefault(selector, Track(selector))
        track.props[prop] = _ordered(points, self.duration)
        track.rest[prop] = points[-1][1] if rest is None else rest
        if origin:
            track.origin = origin
        if wraps:
            track.wraps.add(prop)

    def css(self, name: str) -> str:
        """Keyframes and rules for every track; identical tracks share one @keyframes."""
        frames: dict[str, str] = {}
        rules = []
        count = "infinite" if self.loop else "1"
        for track in self.tracks.values():
            body = self._keyframes(track)
            rest = _declarations({p: v for p, v in track.rest.items() if not _same(v, DEFAULTS[p])})
            extra = (
                f" transform-box: fill-box; transform-origin: {track.origin};"
                if track.origin
                else ""
            )
            if body is None:
                if rest or extra:
                    rules.append(f"{track.selector} {{{rest}{extra} }}")
                continue
            key = frames.setdefault(body, f"{name}-k{len(frames)}")
            rules.append(
                f"{track.selector} {{{rest}{extra} "
                f"animation: {key} {self.duration:.3f}s linear {count} both; }}"
            )
        keyframes = "".join(f"@keyframes {key} {{{body}}}\n" for body, key in frames.items())
        return keyframes + "\n".join(rules) + ("\n" if rules else "")

    def _keyframes(self, track: Track) -> str | None:
        props = {
            p: points if p in track.wraps else self._closed(points)
            for p, points in track.props.items()
        }
        if all(
            len({_key(v) for _, v in pts}) == 1 and _same(pts[0][1], track.rest[p])
            for p, pts in props.items()
        ):
            return None
        times = sorted({0.0, self.duration, *(t for pts in props.values() for t, _ in pts)})
        rows = [(t, {p: _at(pts, t) for p, pts in props.items()}) for t in times]
        kept = [
            row
            for i, row in enumerate(rows)
            if i in (0, len(rows) - 1)
            or not (_same_row(rows[i - 1][1], row[1]) and _same_row(row[1], rows[i + 1][1]))
        ]
        return "".join(
            f" {_percent(t, self.duration)} {{{_declarations(values)} }}" for t, values in kept
        )

    def _closed(self, points: list[Point]) -> list[Point]:
        """A looping track eases back to its first value at the end of the loop."""
        if not self.loop or _same(points[-1][1], points[0][1]):
            return points
        end = self.duration
        last_t = points[-1][0]
        start = max(last_t, end - TAU)
        if start >= end:
            return [*points[:-1], (end, points[0][1])]
        return [*points, (start, points[-1][1]), (end, points[0][1])]


# ----------------------------------------------------------------- track shapes
def changes(initial: Value, moves: Iterable[tuple[float, Value]], tau: float = TAU) -> list[Point]:
    """A value that holds, then eases to a new value at each (time, value) over `tau`."""
    points: list[Point] = [(0.0, initial)]
    current = initial
    ordered = sorted(moves, key=lambda m: m[0])
    for i, (t, value) in enumerate(ordered):
        if _same(value, current):
            continue
        limit = ordered[i + 1][0] if i + 1 < len(ordered) else t + tau
        end = min(t + tau, max(limit, t + 0.01))
        points.append((max(t, points[-1][0]), current))
        points.append((end, value))
        current = value
    return points


def window(start: float, end: float, ramp: float = 0.12, peak: float = 1.0) -> list[Point]:
    """Opacity that is 0, rises to `peak` at `start`, and falls back to 0 by `end`."""
    ramp = min(ramp, max(0.01, (end - start) / 3))
    return [
        (0.0, 0.0),
        (max(0.0, start - ramp), 0.0),
        (start, peak),
        (max(start, end - ramp), peak),
        (end, 0.0),
    ]


def eased(
    start: float, end: float, a: float, b: float, samples: int = 8
) -> list[tuple[float, float]]:
    """Points from a to b between two times, easing in and out (a sine curve)."""
    out: list[tuple[float, float]] = []
    for i in range(samples + 1):
        f = i / samples
        out.append((start + (end - start) * f, a + (b - a) * (0.5 - 0.5 * math.cos(math.pi * f))))
    return out


def periodic(period: float, duration: float, samples: int = 16) -> list[tuple[float, float]]:
    """(time, cycles) samples of a repeating motion: cycles counts up from 0 by 1 a period.

    The period is stretched a little so a whole number of cycles fills the loop, so the
    motion joins up when the animation starts over.
    """
    loops = max(1, round(duration / max(period, 0.2)))
    step = duration / loops / samples
    return [(i * step, i / samples) for i in range(loops * samples + 1)]


# ---------------------------------------------------------------------- helpers
def _ordered(points: Sequence[Point], duration: float) -> list[Point]:
    out: list[Point] = []
    for t, v in sorted(points, key=lambda p: p[0]):
        t = min(max(t, 0.0), duration)
        if out and t <= out[-1][0]:
            t = out[-1][0]
        out.append((t, v))
    if out[0][0] > 0:
        out.insert(0, (0.0, out[0][1]))
    return out


def _at(points: Sequence[Point], t: float) -> Value:
    if t <= points[0][0]:
        return points[0][1]
    for (t0, v0), (t1, v1) in zip(points, points[1:], strict=False):
        if t0 <= t <= t1:
            if t1 - t0 < 1e-9:
                return v1
            f = (t - t0) / (t1 - t0)
            return _mix(v0, v1, f)
    return points[-1][1]


def _mix(a: Value, b: Value, f: float) -> Value:
    if isinstance(a, tuple) and isinstance(b, tuple):
        return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
    if isinstance(a, tuple) or isinstance(b, tuple):
        raise ValueError("a track mixes one number with a pair")
    return a + (b - a) * f


def _key(v: Value) -> tuple[float, ...]:
    return tuple(round(x, 3) for x in v) if isinstance(v, tuple) else (round(v, 3),)


def _same(a: Value, b: Value) -> bool:
    return _key(a) == _key(b)


def _same_row(a: dict[str, Value], b: dict[str, Value]) -> bool:
    return all(_same(a[p], b[p]) for p in a)


def _percent(t: float, duration: float) -> str:
    text = f"{100 * t / duration:.3f}".rstrip("0").rstrip(".")
    return f"{text}%"


def _declarations(values: dict[str, Value]) -> str:
    out = []
    for prop, v in values.items():
        if prop == "translate" and isinstance(v, tuple):
            out.append(f" translate: {v[0]:.2f}px {v[1]:.2f}px;")
        elif prop == "scale" and isinstance(v, tuple):
            out.append(f" scale: {v[0]:.3f} {v[1]:.3f};")
        elif isinstance(v, tuple):
            raise ValueError(f"{prop} takes one number")
        elif prop == "rotate":
            out.append(f" rotate: {v:.2f}deg;")
        elif prop == "stroke-dashoffset":
            out.append(f" stroke-dashoffset: {v:.2f}px;")
        else:
            out.append(f" {prop}: {v:.3f};")
    return "".join(out)


def held(points: Sequence[Point]) -> list[Point]:
    """Points with times kept in order, so a jump while a part is hidden stays a jump."""
    out: list[Point] = []
    for t, v in points:
        out.append((max(t, out[-1][0]) if out else t, v))
    return out


def redraws(length: float, starts: Sequence[float], span: float, drawn: bool) -> list[Point]:
    """A dash offset that strokes a line on over `span` at each start.

    Between two starts the line is hidden, so the jump back to undrawn does not show.
    """
    points: list[Point] = [(0.0, 0.0 if drawn else length)]
    for t in starts:
        points += [(max(0.0, t - 0.02), points[-1][1]), (t, length), (t + span, 0.0)]
    return held(points)


def swells(starts: Sequence[float], peak: float = 1.06) -> list[Point]:
    """A scale that swells twice from each start, to catch the eye."""
    points: list[Point] = [(0.0, 1.0)]
    for t in sorted(starts):
        points += [(t, 1.0), (t + 0.3, peak), (t + 0.6, 1.0), (t + 0.9, peak), (t + 1.2, 1.0)]
    return held(points)
