"""Value noise and fractal noise built from upscaled random grids.

Watercolor effects need many noise fields (pigment flow, granulation, ragged edges).
Upscaling a small random grid with bicubic interpolation is fast in OpenCV and smooth
enough that no octave shows its grid.
"""

from __future__ import annotations

import cv2
import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float32]


def value_noise(height: int, width: int, cell: float, rng: np.random.Generator) -> FloatArray:
    """One octave of smooth noise in [0, 1] whose features are about `cell` pixels wide."""
    cell = max(cell, 1.0)
    grid_h = max(2, int(np.ceil(height / cell)) + 3)
    grid_w = max(2, int(np.ceil(width / cell)) + 3)
    grid = rng.random((grid_h, grid_w), dtype=np.float32)
    big = cv2.resize(
        grid,
        (int(grid_w * cell), int(grid_h * cell)),
        interpolation=cv2.INTER_CUBIC,
    )
    # A random offset hides the grid alignment between octaves.
    oy = int(rng.integers(0, max(1, big.shape[0] - height)))
    ox = int(rng.integers(0, max(1, big.shape[1] - width)))
    out = np.asarray(big[oy : oy + height, ox : ox + width], dtype=np.float32)
    return np.clip(out, 0.0, 1.0)


def fbm(
    height: int,
    width: int,
    scale: float,
    rng: np.random.Generator,
    octaves: int = 4,
    persistence: float = 0.5,
) -> FloatArray:
    """Fractal noise in [0, 1]: octaves of value noise, each half the size of the last."""
    total = np.zeros((height, width), dtype=np.float32)
    amplitude = 1.0
    weight = 0.0
    cell = scale
    for _ in range(octaves):
        total += amplitude * value_noise(height, width, cell, rng)
        weight += amplitude
        amplitude *= persistence
        cell = max(cell / 2.0, 1.0)
    total /= weight
    return normalize(total)


def normalize(field: FloatArray) -> FloatArray:
    """Stretch a field to fill [0, 1]; flat fields become 0.5."""
    lo = float(field.min())
    hi = float(field.max())
    if hi - lo < 1e-6:
        return np.full_like(field, 0.5)
    return ((field - lo) / (hi - lo)).astype(np.float32)


def noise1d(length: int, scale: float, rng: np.random.Generator, octaves: int = 3) -> FloatArray:
    """Smooth 1D noise in [-1, 1], used to wobble lines and ridges."""
    length = max(length, 2)
    row = fbm(1, length, scale, rng, octaves=octaves)[0]
    return np.asarray(row * 2.0 - 1.0, dtype=np.float32)
