"""Point-list helpers: resample, smooth and hand-wobble outlines before they are painted."""

from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from chronicle.core.watercolor.noise import noise1d

Points = npt.NDArray[np.float64]
PointLike = Sequence[Sequence[float]]


def as_points(points: PointLike | Points) -> Points:
    """Convert any [[x, y], ...] sequence to an (n, 2) float array."""
    arr = np.asarray(points, dtype=np.float64)
    if arr.ndim != 2 or arr.shape[1] != 2 or arr.shape[0] < 2:
        raise ValueError("expected a list of at least two [x, y] points")
    return arr


def resample(points: Points, step: float, closed: bool) -> Points:
    """Place points every `step` pixels along the outline so wobble noise has room to act."""
    pts = np.vstack([points, points[:1]]) if closed else points
    seg = np.diff(pts, axis=0)
    lengths = np.hypot(seg[:, 0], seg[:, 1])
    total = float(lengths.sum())
    if total < 1e-6:
        return points.copy()
    count = max(int(total / max(step, 0.5)), 4)
    cumulative = np.concatenate([[0.0], np.cumsum(lengths)])
    targets = np.linspace(0.0, total, count, endpoint=not closed)
    xs = np.interp(targets, cumulative, pts[:, 0])
    ys = np.interp(targets, cumulative, pts[:, 1])
    return np.stack([xs, ys], axis=1)


def wobble(
    points: Points, amplitude: float, scale: float, rng: np.random.Generator, closed: bool
) -> Points:
    """Push each point along its normal by smooth noise, the unsteadiness of a hand."""
    if amplitude <= 0:
        return points
    n = len(points)
    offsets = noise1d(n, max(scale, 2.0), rng) * amplitude
    nxt = np.roll(points, -1, axis=0)
    prv = np.roll(points, 1, axis=0)
    if not closed:
        nxt[-1] = points[-1] + (points[-1] - points[-2])
        prv[0] = points[0] - (points[1] - points[0])
    tangent = nxt - prv
    norm = np.hypot(tangent[:, 0], tangent[:, 1])
    norm[norm < 1e-9] = 1.0
    normal = np.stack([-tangent[:, 1] / norm, tangent[:, 0] / norm], axis=1)
    return points + normal * offsets[:, None]


def smooth(points: Points, closed: bool, samples: int = 8) -> Points:
    """Catmull-Rom spline through the points, for organic curves from a few control points."""
    n = len(points)
    if n < 3:
        return points
    out: list[npt.NDArray[np.float64]] = []
    count = n if closed else n - 1
    for i in range(count):
        p0 = points[(i - 1) % n] if closed or i > 0 else points[0]
        p1 = points[i % n]
        p2 = points[(i + 1) % n]
        p3 = points[(i + 2) % n] if closed or i + 2 < n else points[-1]
        for t in np.linspace(0.0, 1.0, samples, endpoint=False):
            t2 = t * t
            t3 = t2 * t
            out.append(
                0.5
                * (
                    (2 * p1)
                    + (-p0 + p2) * t
                    + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t3
                )
            )
    if not closed:
        out.append(points[-1])
    return np.asarray(out, dtype=np.float64)


def ellipse(cx: float, cy: float, rx: float, ry: float, steps: int = 64) -> Points:
    """Outline of an axis-aligned ellipse."""
    angles = np.linspace(0.0, 2.0 * math.pi, steps, endpoint=False)
    return np.stack([cx + rx * np.cos(angles), cy + ry * np.sin(angles)], axis=1)


def blob(
    cx: float, cy: float, rx: float, ry: float, rng: np.random.Generator, lumpiness: float = 0.25
) -> Points:
    """Irregular rounded shape: an ellipse whose radius varies with smooth noise."""
    steps = 72
    angles = np.linspace(0.0, 2.0 * math.pi, steps, endpoint=False)
    bumps = noise1d(steps + 8, 9.0, rng)[:steps]
    bumps = bumps - np.linspace(0.0, 1.0, steps) * (bumps[-1] - bumps[0])
    radius = 1.0 + lumpiness * bumps
    return np.stack([cx + rx * radius * np.cos(angles), cy + ry * radius * np.sin(angles)], axis=1)


def ridge(
    x0: float,
    x1: float,
    base_y: float,
    amplitude: float,
    rng: np.random.Generator,
    roughness: float = 140.0,
    step: float = 6.0,
) -> Points:
    """A horizon line: y varies with fractal noise between x0 and x1."""
    count = max(int((x1 - x0) / step), 8)
    xs = np.linspace(x0, x1, count)
    ys = (
        base_y
        - (noise1d(count, max(roughness / step, 2.0), rng, octaves=4) + 1.0) * 0.5 * amplitude
    )
    return np.stack([xs, ys], axis=1)


def close_down(line: Points, bottom: float) -> Points:
    """Turn a left-to-right line into a filled shape reaching down to `bottom`."""
    return np.vstack([line, [[line[-1, 0], bottom], [line[0, 0], bottom]]])
