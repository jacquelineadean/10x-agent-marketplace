"""The painting surface: transparent washes, pen lines and splatter on textured paper.

Model (after Curtis et al. 1997 and Bousseau et al. 2006, simplified for image space):
each wash is a pigment density field. Density rises at the wash rim (edge darkening),
drifts with low-frequency noise (pigment flow), settles into paper valleys
(granulation) and is pushed outward by backruns (blooms). Washes multiply onto the
paper: `rgb *= 1 - density * (1 - pigment)`, so layers glaze like transparent paint.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

import cv2
import numpy as np
import numpy.typing as npt

from chronicle.core.watercolor.geometry import (
    PointLike,
    Points,
    as_points,
    blob,
    resample,
    wobble,
)
from chronicle.core.watercolor.noise import FloatArray, fbm, noise1d
from chronicle.core.watercolor.paper import Paper, make_paper
from chronicle.core.watercolor.pigments import pigment_rgb

PAPER_WHITE = (0.995, 0.988, 0.972)
Shape = PointLike | Points
# Gradient line start and end in scene px, then stops of (offset, rgb, strength).
ColorRamp = tuple[
    tuple[float, float],
    tuple[float, float],
    Sequence[tuple[float, tuple[float, float, float], float]],
]


@dataclass(frozen=True)
class Box:
    """A crop of the canvas in render pixels."""

    x0: int
    y0: int
    x1: int
    y1: int

    @property
    def width(self) -> int:
        return self.x1 - self.x0

    @property
    def height(self) -> int:
        return self.y1 - self.y0


def _gauss(field: FloatArray, sigma: float) -> FloatArray:
    if sigma <= 0.05:
        return field
    return np.asarray(cv2.GaussianBlur(field, (0, 0), sigma), dtype=np.float32)


def _smoothstep(lo: float, hi: float, field: FloatArray) -> FloatArray:
    t = np.clip((field - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    return np.asarray(t * t * (3.0 - 2.0 * t), dtype=np.float32)


class Canvas:
    """A sheet of watercolor paper of `width` x `height` scene pixels.

    `scale` renders the same scene larger or smaller; every size argument stays in
    scene pixels, so a scene looks the same at any scale.
    """

    def __init__(
        self,
        width: int,
        height: int,
        seed: int,
        scale: float = 1.0,
        paper: Paper | None = None,
    ) -> None:
        self.scene_width = width
        self.scene_height = height
        self.scale = scale
        self.width = max(8, round(width * scale))
        self.height = max(8, round(height * scale))
        self.rng = np.random.default_rng(seed)
        self.paper = paper or make_paper(self.height, self.width, self.rng, scale)
        self.rgb = np.empty((self.height, self.width, 3), dtype=np.float32)
        self.rgb[:] = PAPER_WHITE
        self.coverage = np.zeros((self.height, self.width), dtype=np.float32)

    # ------------------------------------------------------------------ helpers
    def _prepare(self, shape: Shape, step: float, amp: float, closed: bool) -> Points:
        pts = as_points(shape) * self.scale
        pts = resample(pts, step * self.scale, closed=closed)
        if amp > 0:
            pts = wobble(pts, amp * self.scale, 14.0, self.rng, closed=closed)
            pts = wobble(pts, amp * 0.35 * self.scale, 3.0, self.rng, closed=closed)
        return pts

    def _box(self, polys: Iterable[Points], pad: float) -> Box | None:
        stacked = np.vstack(list(polys))
        x0 = max(0, int(math.floor(stacked[:, 0].min() - pad)))
        y0 = max(0, int(math.floor(stacked[:, 1].min() - pad)))
        x1 = min(self.width, int(math.ceil(stacked[:, 0].max() + pad)))
        y1 = min(self.height, int(math.ceil(stacked[:, 1].max() + pad)))
        if x1 - x0 < 2 or y1 - y0 < 2:
            return None
        return Box(x0, y0, x1, y1)

    @staticmethod
    def _fill(polys: Sequence[Points], box: Box, evenodd: bool = False) -> FloatArray:
        mask = np.zeros((box.height, box.width), dtype=np.uint8)
        origin = np.array([box.x0, box.y0], dtype=np.float64)
        if evenodd:
            outlines = [np.round((poly - origin) * 16.0).astype(np.int32) for poly in polys]
            cv2.fillPoly(mask, outlines, 255, cv2.LINE_AA, shift=4)
            return mask.astype(np.float32) / 255.0
        # One polygon per call: filling them together would use the even-odd rule and
        # punch holes wherever two shapes overlap.
        for poly in polys:
            layer = np.zeros_like(mask)
            cv2.fillPoly(
                layer,
                [np.round((poly - origin) * 16.0).astype(np.int32)],
                255,
                cv2.LINE_AA,
                shift=4,
            )
            np.maximum(mask, layer, out=mask)
        return mask.astype(np.float32) / 255.0

    def _noise(self, box: Box, scale: float, octaves: int = 3) -> FloatArray:
        return fbm(box.height, box.width, max(scale * self.scale, 1.0), self.rng, octaves=octaves)

    def _glaze(self, box: Box, density: FloatArray, color: npt.NDArray[np.float32]) -> None:
        region = self.rgb[box.y0 : box.y1, box.x0 : box.x1]
        region *= 1.0 - density[..., None] * (1.0 - color)
        cov = self.coverage[box.y0 : box.y1, box.x0 : box.x1]
        np.maximum(cov, np.clip(density, 0.0, 1.0), out=cov)

    # ------------------------------------------------------------------- washes
    def wash(
        self,
        shapes: Sequence[Shape],
        pigment: str,
        *,
        opacity: float = 0.55,
        edge: float = 0.45,
        wet: float = 0.0,
        granulation: float = 0.35,
        flow: float = 0.35,
        wobble_px: float = 2.0,
        blooms: int = 0,
        pigment2: str | None = None,
        gradient: tuple[float, float, float] | None = None,
        holes: Sequence[Shape] = (),
        lift: bool = False,
        occlude: bool = False,
        evenodd: bool = False,
        ramp: ColorRamp | None = None,
    ) -> None:
        """Lay one flat or graded wash over the union of `shapes`.

        gradient is (angle in degrees, density at start, density at end): 90 fades top
        to bottom. lift removes pigment instead, the way a damp brush lifts a cloud.
        occlude first clears whatever lies under the exact same outline, so a near object
        hides a far one instead of glazing over it. evenodd fills the shapes together, so
        an inner outline cuts a hole the way SVG paths do. ramp blends colors wet-in-wet
        along a line, for an SVG linear gradient.
        """
        if not shapes:
            return
        polys = [self._prepare(s, 3.0, wobble_px, closed=True) for s in shapes]
        pad = (8.0 + wet * 36.0) * self.scale
        box = self._box(polys, pad)
        if box is None:
            return
        mask = self._fill(polys, box, evenodd)
        if holes:
            hole_polys = [self._prepare(h, 3.0, wobble_px, closed=True) for h in holes]
            mask *= 1.0 - self._fill(hole_polys, box)

        if wet > 0:
            sigma = (1.2 + wet * 13.0) * self.scale
            soft = _gauss(mask, sigma)
            ragged = self._noise(box, 22.0, octaves=3)
            shifted = soft + (ragged - 0.5) * 0.55 * wet * (soft * (1.0 - soft) * 4.0)
            m = _smoothstep(0.08, 0.92, np.asarray(shifted, dtype=np.float32))
        else:
            m = _gauss(mask, 0.55 * self.scale)

        modifier = np.ones_like(m)
        edge_strength = edge * (1.0 - 0.75 * min(wet, 1.0))
        if edge_strength > 0:
            rim = np.clip((m - _gauss(m, 3.2 * self.scale)) * 2.4, 0.0, 1.0)
            rim_var = self._noise(box, 45.0, octaves=2)
            modifier *= 1.0 + edge_strength * rim * (0.45 + 1.1 * rim_var) * 1.6
        if flow > 0:
            drift = self._noise(box, 110.0, octaves=3)
            modifier *= 1.0 + flow * (drift - 0.5) * 1.3
        if granulation > 0:
            tooth = self.paper.height[box.y0 : box.y1, box.x0 : box.x1]
            specks = self._noise(box, 2.2, octaves=2)
            modifier *= 1.0 + granulation * ((0.5 - tooth) * 0.7 + (specks - 0.5) * 0.25)
        if gradient is not None:
            modifier *= self._ramp(box, mask, gradient)
        for _ in range(max(blooms, 0)):
            modifier *= self._bloom(box, mask)

        color = self._pigment_field(box, pigment, pigment2)
        if ramp is not None:
            color, strength = self._color_ramp(box, ramp)
            modifier *= strength
        density = np.clip(opacity * m * modifier, 0.0, 1.0).astype(np.float32)
        if occlude:
            region = self.rgb[box.y0 : box.y1, box.x0 : box.x1]
            region += m[..., None] * (np.array(PAPER_WHITE, np.float32) - region)
        if lift:
            region = self.rgb[box.y0 : box.y1, box.x0 : box.x1]
            region += density[..., None] * (np.array(PAPER_WHITE, np.float32) - region)
            return
        self._glaze(box, density, color)

    def reserve(self, shapes: Sequence[Shape], *, softness: float = 0.0) -> None:
        """Return an area to bare paper, as if the painter had worked around it."""
        self.wash(
            shapes,
            "ink",
            opacity=1.0,
            edge=0.0,
            wet=softness,
            granulation=0.0,
            flow=0.0,
            wobble_px=1.0,
            lift=True,
        )

    def glow(self, cx: float, cy: float, radius: float, pigment: str, opacity: float) -> None:
        """A soft radial wash that fades to nothing, for a sun or a lamp."""
        r = radius * self.scale
        box = self._box([np.array([[cx * self.scale, cy * self.scale]])], r * 1.2)
        if box is None:
            return
        gy, gx = np.mgrid[box.y0 : box.y1, box.x0 : box.x1].astype(np.float32)
        dist = np.hypot(gx - cx * self.scale, gy - cy * self.scale) / max(r, 1.0)
        density = opacity * np.clip(1.0 - dist, 0.0, 1.0) ** 1.6
        density *= 0.85 + 0.3 * self._noise(box, 60.0, octaves=2)
        color = np.array(pigment_rgb(pigment), dtype=np.float32).reshape(1, 1, 3)
        self._glaze(box, density.astype(np.float32), color)

    def drybrush(
        self,
        shapes: Sequence[Shape],
        pigment: str,
        *,
        opacity: float = 0.6,
        angle: float = 0.0,
        coverage: float = 0.55,
    ) -> None:
        """A dragged brush that skips over the paper tooth and leaves broken streaks."""
        polys = [self._prepare(s, 3.0, 2.0, closed=True) for s in shapes]
        box = self._box(polys, 4.0 * self.scale)
        if box is None:
            return
        mask = _gauss(self._fill(polys, box), 0.6 * self.scale)
        long_side = max(box.width, box.height) * 2
        # Noise that changes fast across the stroke and slowly along it reads as bristles.
        across = fbm(long_side, max(long_side // 14, 4), 2.5 * self.scale, self.rng, octaves=2)
        streak = cv2.resize(across, (long_side, long_side), interpolation=cv2.INTER_LINEAR)
        breakup = fbm(long_side, long_side, 26.0 * self.scale, self.rng, octaves=2)
        streak = streak * (0.55 + 0.45 * breakup)
        rot = cv2.getRotationMatrix2D((long_side / 2, long_side / 2), -angle, 1.0)
        streak = cv2.warpAffine(streak, rot, (long_side, long_side))
        oy = (long_side - box.height) // 2
        ox = (long_side - box.width) // 2
        streaks = np.asarray(streak[oy : oy + box.height, ox : ox + box.width], dtype=np.float32)
        tooth = self.paper.height[box.y0 : box.y1, box.x0 : box.x1]
        catch = _smoothstep(
            1.0 - coverage - 0.12, 1.0 - coverage + 0.12, 0.6 * streaks + 0.4 * tooth
        )
        density = np.clip(mask * catch * opacity, 0.0, 1.0).astype(np.float32)
        color = np.array(pigment_rgb(pigment), dtype=np.float32).reshape(1, 1, 3)
        self._glaze(box, density, color)

    def reflect(
        self,
        waterline: float,
        depth: float,
        *,
        strength: float = 0.55,
        x0: float = 0.0,
        x1: float | None = None,
    ) -> None:
        """Mirror what is painted above `waterline` into the water below, rippled and blurred."""
        s = self.scale
        top = int(waterline * s)
        rows = min(int(depth * s), top, self.height - top)
        if rows < 4:
            return
        left = max(0, int(x0 * s))
        right = min(self.width, int((x1 if x1 is not None else self.scene_width) * s))
        white = np.array(PAPER_WHITE, dtype=np.float32)
        source = self.rgb[top - rows : top, left:right][::-1] / white
        ripple = noise1d(rows, 6.0, self.rng) * 5.0 * s
        shifted = np.empty_like(source)
        for i in range(rows):
            shifted[i] = np.roll(source[i], int(ripple[i] * (0.3 + i / rows)), axis=0)
        k = max(3, int(31 * s) | 1)
        blurred = cv2.blur(shifted, (k, max(1, int(3 * s))))
        fade = np.linspace(1.0, 0.25, rows, dtype=np.float32)[:, None, None] * strength
        tone = 1.0 - fade * (1.0 - np.clip(blurred, 0.0, 1.0) ** 1.7)
        self.rgb[top : top + rows, left:right] *= tone.astype(np.float32)

    def _pigment_field(
        self, box: Box, pigment: str, pigment2: str | None
    ) -> npt.NDArray[np.float32]:
        first = np.array(pigment_rgb(pigment), dtype=np.float32)
        if pigment2 is None:
            return first.reshape(1, 1, 3)
        second = np.array(pigment_rgb(pigment2), dtype=np.float32)
        mix = _smoothstep(0.3, 0.7, self._noise(box, 140.0, octaves=2))[..., None]
        return np.asarray(first * (1.0 - mix) + second * mix, dtype=np.float32)

    def _color_ramp(self, box: Box, ramp: ColorRamp) -> tuple[npt.NDArray[np.float32], FloatArray]:
        """Per-pixel color and strength from gradient stops, with a ragged wet-in-wet blend."""
        (x0, y0), (x1, y1), stops = ramp
        s = self.scale
        dx, dy = (x1 - x0) * s, (y1 - y0) * s
        span = dx * dx + dy * dy or 1.0
        gy, gx = np.mgrid[box.y0 : box.y1, box.x0 : box.x1].astype(np.float32)
        t = ((gx - x0 * s) * dx + (gy - y0 * s) * dy) / span
        t = t + (self._noise(box, 60.0, octaves=3) - 0.5) * 0.18
        offsets = [stop[0] for stop in stops]
        color = np.empty((box.height, box.width, 3), dtype=np.float32)
        for channel in range(3):
            color[..., channel] = np.interp(t, offsets, [stop[1][channel] for stop in stops])
        strength = np.interp(t, offsets, [stop[2] for stop in stops]).astype(np.float32)
        return color, strength

    def _ramp(self, box: Box, mask: FloatArray, gradient: tuple[float, float, float]) -> FloatArray:
        angle, start, end = gradient
        ys, xs = np.nonzero(mask > 0.5)
        if len(xs) == 0:
            return np.ones_like(mask)
        rad = math.radians(angle)
        dx, dy = math.cos(rad), math.sin(rad)
        gy, gx = np.mgrid[0 : box.height, 0 : box.width].astype(np.float32)
        proj = gx * dx + gy * dy
        inside = xs * dx + ys * dy
        lo, hi = float(inside.min()), float(inside.max())
        t = np.clip((proj - lo) / max(hi - lo, 1.0), 0.0, 1.0)
        return np.asarray(start + (end - start) * t, dtype=np.float32)

    def _bloom(self, box: Box, mask: FloatArray) -> FloatArray:
        ys, xs = np.nonzero(mask > 0.9)
        if len(xs) == 0:
            return np.ones_like(mask)
        pick = int(self.rng.integers(0, len(xs)))
        size = min(box.width, box.height) * float(self.rng.uniform(0.12, 0.3))
        outline = blob(float(xs[pick]), float(ys[pick]), size, size * 0.8, self.rng, 0.45)
        outline = wobble(resample(outline, 2.0, True), size * 0.06, 4.0, self.rng, True)
        local = Box(0, 0, box.width, box.height)
        bloom = _gauss(self._fill([outline], local), 1.5 * self.scale)
        outer = np.clip((_gauss(bloom, 3.0 * self.scale) - bloom) * 3.0, 0.0, 1.0)
        return np.asarray(1.0 - 0.42 * bloom + 0.75 * outer, dtype=np.float32)

    # -------------------------------------------------------------------- lines
    def ink(
        self,
        points: Shape,
        *,
        width: float = 1.4,
        pigment: str = "ink",
        opacity: float = 0.85,
        jitter: float = 0.7,
        taper: float = 0.18,
        breaks: float = 0.0,
        closed: bool = False,
        lift: bool = False,
    ) -> None:
        """A pen line that wavers, swells and thins like a dip pen on cold-press paper.

        lift scrubs the paint back to paper along the line instead: a highlight on
        glass or metal.
        """
        pts = as_points(points) * self.scale
        if closed:
            pts = np.vstack([pts, pts[:1]])
        pts = resample(pts, 1.2 * self.scale, closed=False)
        if jitter > 0:
            pts = wobble(pts, jitter * self.scale, 40.0, self.rng, closed=False)
            pts = wobble(pts, jitter * 0.3 * self.scale, 6.0, self.rng, closed=False)
        n = len(pts)
        swell = 0.78 + 0.22 * noise1d(n, 30.0, self.rng)
        t = np.linspace(0.0, 1.0, n)
        if taper > 0:
            envelope = np.minimum(1.0, np.minimum(t, 1.0 - t) / taper)
            swell *= 0.35 + 0.65 * np.sqrt(np.clip(envelope, 0.0, 1.0))
        keep = np.ones(n, dtype=bool)
        if breaks > 0:
            keep = noise1d(n, 25.0, self.rng) > (breaks * 2.0 - 1.0)
        radii = np.maximum(width * self.scale * swell * 0.5, 0.35)
        box = self._box([pts], float(radii.max()) + 3.0)
        if box is None:
            return
        factor = 3
        layer = np.zeros((box.height * factor, box.width * factor), dtype=np.uint8)
        for (x, y), r, on in zip(pts, radii, keep, strict=True):
            if not on:
                continue
            center = (
                int(round((x - box.x0) * factor * 16)),
                int(round((y - box.y0) * factor * 16)),
            )
            cv2.circle(layer, center, max(int(r * factor * 16), 8), 255, -1, cv2.LINE_AA, 4)
        stroke = cv2.resize(layer, (box.width, box.height), interpolation=cv2.INTER_AREA)
        tooth = self.paper.height[box.y0 : box.y1, box.x0 : box.x1]
        density = stroke.astype(np.float32) / 255.0 * opacity * (0.8 + 0.35 * tooth)
        density = np.clip(density, 0.0, 1.0).astype(np.float32)
        if lift:
            region = self.rgb[box.y0 : box.y1, box.x0 : box.x1]
            region += density[..., None] * (np.array(PAPER_WHITE, np.float32) - region)
            return
        color = np.array(pigment_rgb(pigment), dtype=np.float32).reshape(1, 1, 3)
        self._glaze(box, density, color)

    def pencil(self, points: Shape, *, closed: bool = False, opacity: float = 0.42) -> None:
        """A light graphite construction line, drawn twice slightly apart."""
        for _ in range(2):
            self.ink(
                points,
                width=0.9,
                pigment="graphite",
                opacity=opacity,
                jitter=1.1,
                taper=0.08,
                breaks=0.15,
                closed=closed,
            )

    def splatter(
        self,
        cx: float,
        cy: float,
        radius: float,
        count: int,
        pigment: str,
        *,
        size: tuple[float, float] = (0.8, 3.2),
        opacity: float = 0.6,
    ) -> None:
        """Flicked droplets scattered around a point."""
        drops = []
        for _ in range(count):
            angle = float(self.rng.uniform(0, 2 * math.pi))
            dist = radius * math.sqrt(float(self.rng.uniform(0, 1)))
            r = float(self.rng.uniform(*size))
            drops.append(
                blob(cx + math.cos(angle) * dist, cy + math.sin(angle) * dist, r, r, self.rng, 0.2)
            )
        self.wash(drops, pigment, opacity=opacity, edge=0.7, granulation=0.2, flow=0.0, wobble_px=0)

    # ------------------------------------------------------------------- output
    def finish(self, vignette: str = "deckle", margin: float = 28.0) -> npt.NDArray[np.uint8]:
        """Show the paper tooth, fade the painting into the sheet, return 8-bit BGR."""
        fade = self._vignette(vignette, margin)
        white = np.array(PAPER_WHITE, dtype=np.float32)
        painted = white + (self.rgb - white) * fade[..., None]
        light = 1.0 + (self.paper.light - 1.0) * np.maximum(fade, 0.25)
        painted *= light[..., None]
        return to_bgr8(painted)

    def sprite(
        self, opaque: bool = False
    ) -> tuple[npt.NDArray[np.uint8], tuple[int, int, int, int] | None]:
        """Return this canvas as a layer cropped to its paint, and its box.

        A plain layer multiplies onto the painting below. An opaque layer carries alpha
        from paint coverage, so a moving object hides what it passes over. The box is
        (x, y, width, height) in scene pixels, so a page can place the layer.
        """
        ys, xs = np.nonzero(self.coverage > 0.01)
        if len(xs) == 0:
            return to_bgr8(self.rgb[:8, :8]), None
        pad = int(4 * self.scale)
        x0 = max(0, int(xs.min()) - pad)
        y0 = max(0, int(ys.min()) - pad)
        x1 = min(self.width, int(xs.max()) + pad + 1)
        y1 = min(self.height, int(ys.max()) + pad + 1)
        crop = self.rgb[y0:y1, x0:x1]
        s = self.scale
        box = (round(x0 / s), round(y0 / s), round((x1 - x0) / s), round((y1 - y0) / s))
        if not opaque:
            return to_bgr8(crop), box
        alpha = _smoothstep(0.02, 0.35, self.coverage[y0:y1, x0:x1])
        bgra = np.dstack([to_bgr8(crop), np.clip(alpha * 255.0 + 0.5, 0, 255).astype(np.uint8)])
        return np.ascontiguousarray(bgra), box

    def _vignette(self, style: str, margin: float) -> FloatArray:
        if style == "none":
            return np.ones((self.height, self.width), dtype=np.float32)
        if style == "spot":
            return self._spot()
        m = margin * self.scale
        frame = np.zeros((self.height, self.width), dtype=np.float32)
        x0, y0, x1, y1 = m, m, self.width - m, self.height - m
        rect = np.array([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], dtype=np.float64)
        amp = (10.0 if style == "deckle" else 4.0) * self.scale
        outline = resample(rect, 3.0 * self.scale, closed=True)
        outline = wobble(outline, amp, 18.0, self.rng, closed=True)
        outline = wobble(outline, amp * 0.4, 4.0, self.rng, closed=True)
        cv2.fillPoly(frame, [np.round(outline * 16).astype(np.int32)], 1.0, cv2.LINE_AA, 4)
        soft = (6.0 if style == "deckle" else 18.0) * self.scale
        frame = _gauss(frame, soft)
        if style == "deckle":
            grain = fbm(self.height, self.width, 5.0 * self.scale, self.rng, octaves=2)
            frame = _smoothstep(0.0, 1.0, frame * (0.75 + 0.5 * grain))
        return np.clip(frame, 0.0, 1.0).astype(np.float32)

    def _spot(self) -> FloatArray:
        """An organic oval that fades out raggedly: the painting floats on the page."""
        cx, cy = self.width / 2, self.height / 2
        outline = blob(cx, cy, self.width * 0.44, self.height * 0.42, self.rng, 0.18)
        outline = wobble(
            resample(outline, 3.0 * self.scale, True), 8 * self.scale, 10.0, self.rng, True
        )
        frame = np.zeros((self.height, self.width), dtype=np.float32)
        cv2.fillPoly(frame, [np.round(outline * 16).astype(np.int32)], 1.0, cv2.LINE_AA, 4)
        frame = _gauss(frame, 22.0 * self.scale)
        grain = fbm(self.height, self.width, 30.0 * self.scale, self.rng, octaves=3)
        return _smoothstep(0.25, 0.75, frame * (0.7 + 0.6 * grain))


def to_bgr8(rgb: FloatArray) -> npt.NDArray[np.uint8]:
    """Float RGB in [0, 1] to OpenCV's 8-bit BGR order."""
    out = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(out[..., ::-1])
