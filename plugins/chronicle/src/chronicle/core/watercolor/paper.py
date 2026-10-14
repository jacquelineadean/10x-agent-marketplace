"""Cold-press paper: a height map that catches pigment and a light map that shows the tooth."""

from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from chronicle.core.watercolor.noise import FloatArray, fbm, normalize


@dataclass(frozen=True)
class Paper:
    """Paper surface for one canvas.

    height: 0 in the valleys where granulating pigment settles, 1 on the peaks.
    light: multiplier near 1.0 that shades the tooth as if lit from the upper left.
    """

    height: FloatArray
    light: FloatArray


def make_paper(height: int, width: int, rng: np.random.Generator, scale: float = 1.0) -> Paper:
    """Build paper texture; `scale` is render pixels per scene pixel so tooth size stays put."""
    tooth = fbm(height, width, 7.0 * scale, rng, octaves=3, persistence=0.55)
    pits = fbm(height, width, 2.5 * scale, rng, octaves=2, persistence=0.5)
    swell = fbm(height, width, 90.0 * scale, rng, octaves=2)
    fibers = _fibers(height, width, rng, scale)
    surface = normalize(0.55 * tooth + 0.2 * pits + 0.15 * swell + 0.1 * fibers)
    gx = cv2.Sobel(surface, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(surface, cv2.CV_32F, 0, 1, ksize=3)
    relief = np.asarray(-(gx + gy) * 0.5, dtype=np.float32)
    relief = np.asarray(cv2.GaussianBlur(relief, (0, 0), 0.6 * scale), dtype=np.float32)
    span = float(np.percentile(np.abs(relief), 99)) or 1.0
    light = 1.0 + 0.022 * np.clip(relief / span, -1.0, 1.0)
    return Paper(height=surface, light=light.astype(np.float32))


def _fibers(height: int, width: int, rng: np.random.Generator, scale: float) -> FloatArray:
    """Faint short strands pressed into the sheet."""
    layer = np.zeros((height, width), dtype=np.float32)
    count = int(height * width / (900.0 * scale * scale))
    for _ in range(count):
        x = float(rng.uniform(0, width))
        y = float(rng.uniform(0, height))
        angle = float(rng.uniform(0, np.pi))
        length = float(rng.uniform(4, 16)) * scale
        dx = np.cos(angle) * length
        dy = np.sin(angle) * length
        cv2.line(
            layer,
            (int(x), int(y)),
            (int(x + dx), int(y + dy)),
            float(rng.uniform(0.3, 1.0)),
            1,
            cv2.LINE_AA,
        )
    return np.asarray(cv2.GaussianBlur(layer, (0, 0), 0.7 * scale), dtype=np.float32)
