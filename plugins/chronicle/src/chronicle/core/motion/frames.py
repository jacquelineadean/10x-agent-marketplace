"""Which moments to capture, and the contact sheet of steps Claude looks at before sharing."""

from __future__ import annotations

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

from chronicle.core.motion.model import Plan

Image = npt.NDArray[np.uint8]


def times(plan: Plan, fps: float) -> list[float]:
    """Frame times over one pass of the clock; a loop's last frame leads into its first."""
    count = max(1, round(plan.duration * fps))
    return [i / fps for i in range(count)]


def checkpoints(plan: Plan) -> list[float]:
    """The end of each step, when what it shows has settled."""
    return [max(0.0, s.end - 0.15) for s in plan.steps] or [plan.duration / 2]


def samples(plan: Plan) -> list[float]:
    """Moments that between them show every color the animation uses, for the GIF palette."""
    mids = [s.start + s.duration * f for s in plan.steps for f in (0.35, 0.6)]
    return sorted({*checkpoints(plan), *mids, plan.duration * 0.02})


def sheet(images: Sequence[Image], columns: int = 2, width: int = 640) -> Image:
    """Images side by side in rows, each scaled to `width` with a thin gap."""
    import cv2  # the painter's dependency; only raster exports reach here

    small = []
    for image in images:
        h = round(image.shape[0] * width / image.shape[1])
        small.append(
            np.asarray(cv2.resize(image, (width, h), interpolation=cv2.INTER_AREA), np.uint8)
        )
    gap = 8
    cell_h = max(s.shape[0] for s in small)
    rows = (len(small) + columns - 1) // columns
    out = np.full(
        (rows * cell_h + (rows + 1) * gap, columns * width + (columns + 1) * gap, 3), 128, np.uint8
    )
    for k, s in enumerate(small):
        r, c = divmod(k, columns)
        y = gap + r * (cell_h + gap)
        x = gap + c * (width + gap)
        out[y : y + s.shape[0], x : x + width] = s
    return out


def scaled(image: Image, width: int) -> Image:
    """The image at `width` pixels wide, or as it is when already that narrow."""
    if image.shape[1] <= width:
        return image
    import cv2

    h = round(image.shape[0] * width / image.shape[1])
    return np.asarray(cv2.resize(image, (width, h), interpolation=cv2.INTER_AREA), np.uint8)
