"""Landscape motifs: sky, clouds, sun, mountains, hills, trees, grass, water, rain."""

from __future__ import annotations

import math

import numpy as np

from chronicle.core.watercolor.canvas import Canvas
from chronicle.core.watercolor.geometry import Points, blob, close_down, ridge, smooth

MOODS: dict[str, dict[str, str]] = {
    "day": {"top": "cerulean", "top2": "cobalt", "low": "lemon", "shade": "lavender"},
    "dawn": {"top": "cobalt", "top2": "cerulean", "low": "cadmium-orange", "shade": "rose"},
    "dusk": {"top": "ultramarine", "top2": "lavender", "low": "cadmium-orange", "shade": "rose"},
    "storm": {"top": "paynes-grey", "top2": "indigo", "low": "neutral-tint", "shade": "indigo"},
    "mist": {"top": "paynes-grey", "top2": "lavender", "low": "warm-grey", "shade": "lavender"},
}


def sky(
    c: Canvas,
    horizon: float,
    mood: str = "day",
    clouds: int = 5,
    cloud_band: tuple[float, float] = (0.12, 0.55),
    intensity: float = 1.0,
) -> None:
    """Graded sky from deep at the top to warm at the horizon, painted around clouds."""
    if mood not in MOODS:
        raise ValueError(f"unknown sky mood {mood!r}; use one of {', '.join(MOODS)}")
    tones = MOODS[mood]
    w = c.scene_width
    band: list[list[float]] = [
        [-40, -40],
        [w + 40, -40],
        [w + 40, horizon + 30],
        [-40, horizon + 30],
    ]
    storm = mood == "storm"
    rng = c.rng
    shapes: list[list[Points]] = []
    for i in range(clouds):
        t = (i + rng.uniform(0.15, 0.85)) / max(clouds, 1)
        y = horizon * float(rng.uniform(*cloud_band))
        size = float(rng.uniform(0.08, 0.14)) * w * (0.55 + y / horizon)
        shapes.append(cumulus(c, t * w, y, size))
    holes = [] if storm else [p for cloud in shapes for p in cloud]
    c.wash(
        [band],
        tones["top"],
        pigment2=tones["top2"],
        opacity=(0.85 if storm else 0.6) * intensity,
        edge=0.05,
        wet=0.55,
        flow=0.55 if storm else 0.35,
        granulation=0.12,
        gradient=(90, 1.0, 0.12),
        blooms=1 if storm else 0,
        wobble_px=0,
        holes=holes,
    )
    c.wash(
        [band],
        tones["low"],
        opacity=(0.3 if storm else 0.4) * intensity,
        edge=0.0,
        wet=0.9,
        flow=0.3,
        granulation=0.05,
        gradient=(90, 0.0, 1.0),
        wobble_px=0,
    )
    for cloud in shapes:
        pts = np.vstack(cloud)
        x_lo, x_hi = float(pts[:, 0].min()), float(pts[:, 0].max())
        y_lo, y_hi = float(pts[:, 1].min()), float(pts[:, 1].max())
        mid = y_lo + (y_hi - y_lo) * 0.55
        if storm:
            c.wash(cloud, "indigo", opacity=0.35, wet=0.8, edge=0.1, blooms=1)
            continue
        c.wash(cloud, "ink", opacity=0.5, wet=0.6, edge=0.0, granulation=0.0, lift=True)
        belly = [[x_lo, mid], [x_hi, mid], [x_hi, y_hi + 4], [x_lo, y_hi + 4]]
        c.wash(
            [belly],
            tones["shade"],
            opacity=0.2,
            wet=0.95,
            edge=0.0,
            flow=0.3,
            granulation=0.05,
            holes=[],
        )


def cumulus(c: Canvas, x: float, y: float, size: float) -> list[Points]:
    """Outline of a flat-bottomed cloud: overlapping puffs over a level base."""
    rng = c.rng
    puffs: list[Points] = []
    count = int(rng.integers(5, 8))
    for k in range(count):
        offset = (k - (count - 1) / 2) / max(count - 1, 1)
        px = x + offset * size * 1.1 + float(rng.normal(0, size * 0.03))
        bulge = 1.0 - abs(offset) * 1.2
        r = size * (0.12 + 0.17 * max(bulge, 0.1)) * float(rng.uniform(0.85, 1.15))
        puffs.append(blob(px, y - r * 0.45, r * 1.2, r * 0.85, rng, 0.2))
    base = np.array(
        [
            [x - size * 0.62, y - size * 0.06],
            [x + size * 0.62, y - size * 0.06],
            [x + size * 0.5, y + size * 0.05],
            [x - size * 0.5, y + size * 0.05],
        ]
    )
    return [*puffs, base]


def sun(c: Canvas, x: float, y: float, radius: float, pigment: str = "gamboge") -> None:
    """A lifted disc with a warm halo."""
    c.glow(x, y, radius * 4.0, pigment, 0.35)
    c.reserve([blob(x, y, radius, radius, c.rng, 0.04)], softness=0.25)
    c.glow(x, y, radius * 1.1, "lemon", 0.25)


def mountains(
    c: Canvas,
    base: float,
    height: float,
    pigment: str = "lavender",
    pigment2: str | None = None,
    x0: float = -20.0,
    x1: float | None = None,
    roughness: float = 260.0,
    opacity: float = 0.5,
    snow: bool = False,
    seed: int | None = None,
) -> None:
    """A range of peaks, darker at the crest; aerial perspective comes from the pigment."""
    right = x1 if x1 is not None else c.scene_width + 20.0
    rng = np.random.default_rng(seed) if seed is not None else c.rng
    line = ridge(x0, right, base, height, rng, roughness=roughness, step=5.0)
    shape = close_down(line, base + 60)
    c.wash(
        [shape],
        pigment,
        pigment2=pigment2,
        opacity=opacity,
        edge=0.55,
        gradient=(90, 1.15, 0.45),
        granulation=0.45,
        wobble_px=1.0,
    )
    if snow:
        tops = line[line[:, 1] < base - height * 0.72]
        for x, y in tops[::7]:
            cap = [[x - 14, y + 18], [x, y - 1], [x + 14, y + 18]]
            c.reserve([cap], softness=0.3)
    c.ink(line[:: max(1, len(line) // 90)], width=0.9, opacity=0.35, breaks=0.45, jitter=0.6)


def hills(
    c: Canvas,
    base: float,
    height: float,
    pigment: str = "sap-green",
    pigment2: str | None = "yellow-ochre",
    x0: float = -20.0,
    x1: float | None = None,
    opacity: float = 0.55,
    roughness: float = 420.0,
    bottom: float | None = None,
    trees: int = 0,
    seed: int | None = None,
) -> None:
    """Rolling hills with an optional fringe of trees along the crest."""
    right = x1 if x1 is not None else c.scene_width + 20.0
    rng = np.random.default_rng(seed) if seed is not None else c.rng
    line = ridge(x0, right, base, height, rng, roughness=roughness, step=6.0)
    floor = bottom if bottom is not None else base + 80
    c.wash(
        [close_down(line, floor)],
        pigment,
        pigment2=pigment2,
        opacity=opacity,
        edge=0.5,
        gradient=(90, 1.0, 0.7),
        blooms=1,
        wobble_px=1.5,
    )
    for _ in range(trees):
        k = int(rng.integers(0, len(line)))
        x, y = float(line[k, 0]), float(line[k, 1])
        size = float(rng.uniform(5, 11))
        c.wash(
            [blob(x, y - size * 0.6, size * 0.7, size, c.rng, 0.3)],
            "hookers-green",
            opacity=0.55,
            edge=0.6,
            granulation=0.3,
            wobble_px=0.6,
        )


def treeline(
    c: Canvas,
    x0: float,
    x1: float,
    ground: float,
    height: float,
    pigment: str = "hookers-green",
    pigment2: str | None = "sap-green",
    opacity: float = 0.55,
) -> None:
    """A distant belt of trees: one scalloped wash with a darker base."""
    rng = c.rng
    tops: list[list[float]] = []
    x = x0
    while x < x1:
        r = float(rng.uniform(0.25, 0.55)) * height
        tops.append([x + r, ground - height * float(rng.uniform(0.6, 1.0))])
        x += r * float(rng.uniform(0.8, 1.2))
    crowns = [
        blob(px, py + height * 0.4, height * 0.45, height * 0.5, rng, 0.25) for px, py in tops
    ]
    base = [[x0, ground - height * 0.55], [x1, ground - height * 0.55], [x1, ground], [x0, ground]]
    c.wash([*crowns, base], pigment, pigment2=pigment2, opacity=opacity, edge=0.55, blooms=1)
    c.wash(
        [[[x0, ground - height * 0.25], [x1, ground - height * 0.25], [x1, ground], [x0, ground]]],
        "indigo",
        opacity=0.22,
        wet=0.6,
        edge=0.0,
    )


def tree(
    c: Canvas,
    x: float,
    ground: float,
    height: float,
    kind: str = "round",
    pigment: str = "sap-green",
    shade: str = "hookers-green",
) -> None:
    """A single tree in three passes: light crown, mid clusters, dark undersides, then trunk."""
    rng = c.rng
    if kind == "conifer":
        layers = 5
        for k in range(layers):
            t = k / layers
            w = height * (0.32 - 0.22 * t)
            y = ground - height * (0.18 + 0.78 * t)
            tri = [[x - w, y + height * 0.2], [x, y - height * 0.08], [x + w, y + height * 0.2]]
            c.wash(
                [tri],
                shade if k % 2 else pigment,
                opacity=0.65,
                edge=0.6,
                wobble_px=1.5,
                occlude=k == 0,
            )
        c.ink([[x, ground], [x, ground - height * 0.25]], width=2.0, opacity=0.7)
        return
    crown_y = ground - height * 0.62
    width = height * (0.36 if kind == "round" else 0.16)
    crown = blob(x, crown_y, width, height * (0.36 if kind == "round" else 0.42), rng, 0.3)
    c.wash([crown], pigment, pigment2="olive", opacity=0.62, edge=0.45, occlude=True)
    clusters = []
    for _ in range(6):
        cx = x + float(rng.normal(0, width * 0.45))
        cy = crown_y + float(rng.uniform(-0.1, 0.3)) * height * 0.4
        clusters.append(blob(cx, cy, width * 0.38, height * 0.13, rng, 0.35))
    c.wash(clusters, pigment, opacity=0.5, edge=0.6)
    under = [
        blob(
            x + float(rng.normal(0, width * 0.3)),
            crown_y + height * 0.14,
            width * 0.45,
            height * 0.09,
            rng,
            0.4,
        )
        for _ in range(3)
    ]
    c.wash(under, shade, opacity=0.55, edge=0.6, granulation=0.4)
    c.ink([[x, ground], [x + 1, crown_y + height * 0.12]], width=2.2, pigment="sepia", opacity=0.8)
    c.ink(
        [[x, crown_y + height * 0.2], [x - width * 0.35, crown_y + height * 0.02]],
        width=1.0,
        pigment="sepia",
        opacity=0.6,
    )
    c.wash(
        [
            [
                [x - width * 0.7, ground - 2],
                [x + width * 0.9, ground - 2],
                [x + width * 0.8, ground + 5],
                [x - width * 0.6, ground + 5],
            ]
        ],
        "indigo",
        opacity=0.18,
        wet=0.6,
        edge=0.0,
    )


def grass(
    c: Canvas,
    x0: float,
    x1: float,
    top: float,
    bottom: float,
    pigment: str = "sap-green",
    pigment2: str | None = "raw-sienna",
    tufts: int = 30,
) -> None:
    """A bank of grass: graded wash, dragged dry-brush and a few inked blades."""
    rng = c.rng
    edge_line = ridge(x0, x1, top + 6, 12, rng, roughness=120, step=8)
    shape = close_down(edge_line, bottom)
    c.wash(
        [shape],
        pigment,
        pigment2=pigment2,
        opacity=0.55,
        edge=0.5,
        blooms=1,
        gradient=(90, 0.7, 1.1),
    )
    c.drybrush([shape], "hookers-green", opacity=0.4, angle=-8, coverage=0.35)
    for _ in range(tufts):
        bx = float(rng.uniform(x0, x1))
        by = float(rng.uniform(top + 8, bottom))
        for _ in range(3):
            lean = float(rng.normal(0, 4))
            h = float(rng.uniform(6, 14)) * (0.6 + (by - top) / max(bottom - top, 1.0))
            c.ink(
                [[bx, by], [bx + lean, by - h]],
                width=0.9,
                pigment="hookers-green",
                opacity=0.6,
                taper=0.4,
                jitter=0.3,
            )


def water(
    c: Canvas,
    shape: list[list[float]],
    pigment: str = "cerulean",
    pigment2: str | None = "paynes-grey",
    opacity: float = 0.5,
    ripples: int = 40,
) -> None:
    """A body of water: graded wash, lifted glints and short inked ripples."""
    rng = c.rng
    c.wash(
        [shape],
        pigment,
        pigment2=pigment2,
        opacity=opacity,
        edge=0.25,
        flow=0.5,
        gradient=(90, 0.55, 1.0),
        wobble_px=0.8,
    )
    pts = np.asarray(shape, dtype=np.float64)
    x_lo, x_hi = float(pts[:, 0].min()), float(pts[:, 0].max())
    y_lo, y_hi = float(pts[:, 1].min()), float(pts[:, 1].max())
    for _ in range(ripples):
        x = float(rng.uniform(x_lo, x_hi))
        y = float(rng.uniform(y_lo + 6, y_hi))
        length = float(rng.uniform(10, 50)) * (0.4 + (y - y_lo) / max(y_hi - y_lo, 1.0))
        if rng.random() < 0.5:
            c.reserve([[[x, y], [x + length, y - 0.6], [x + length, y + 1.4], [x, y + 1.8]]])
        else:
            c.ink(
                [[x, y], [x + length * 0.6, y + 0.4]],
                width=0.8,
                pigment="paynes-grey",
                opacity=0.45,
                taper=0.45,
            )


def rain(
    c: Canvas,
    count: int = 400,
    angle: float = 12.0,
    length: tuple[float, float] = (18.0, 42.0),
    pigment: str = "paynes-grey",
    opacity: float = 0.35,
    area: tuple[float, float, float, float] | None = None,
) -> None:
    """Slanted streaks of rain over an area (x0, y0, x1, y1), default the whole sheet."""
    x0, y0, x1, y1 = area or (0.0, 0.0, float(c.scene_width), float(c.scene_height))
    rng = c.rng
    dx = math.sin(math.radians(angle))
    dy = math.cos(math.radians(angle))
    for _ in range(count):
        x = float(rng.uniform(x0, x1))
        y = float(rng.uniform(y0, y1))
        ln = float(rng.uniform(*length))
        c.ink(
            [[x, y], [x - dx * ln, y + dy * ln]],
            width=0.8,
            pigment=pigment,
            opacity=opacity,
            jitter=0.1,
            taper=0.5,
        )


def birds(c: Canvas, x: float, y: float, count: int = 5, spread: float = 120.0) -> None:
    """Distant birds drawn as two quick pen curves each."""
    rng = c.rng
    for _ in range(count):
        bx = x + float(rng.uniform(-spread, spread))
        by = y + float(rng.uniform(-spread * 0.35, spread * 0.35))
        s = float(rng.uniform(5, 10))
        flap = float(rng.uniform(-0.4, 0.5))
        left = smooth(
            np.array([[bx - s, by - s * (0.2 + flap)], [bx - s * 0.45, by - s * 0.45], [bx, by]]),
            closed=False,
            samples=6,
        )
        right = smooth(
            np.array([[bx, by], [bx + s * 0.45, by - s * 0.45], [bx + s, by - s * (0.2 + flap)]]),
            closed=False,
            samples=6,
        )
        c.ink(left, width=1.3, opacity=0.8, taper=0.3, jitter=0.15)
        c.ink(right, width=1.3, opacity=0.8, taper=0.3, jitter=0.15)


def bank(
    c: Canvas,
    outline: list[list[float]],
    pigment: str = "sap-green",
    pigment2: str | None = "olive",
    shade: str = "hookers-green",
    bushes: int = 6,
    reeds: int = 18,
) -> None:
    """A grassy hillside in front of everything else: occludes, then paints, then details.

    `outline` is a closed shape; its lowest edge should run off the bottom of the sheet.
    """
    rng = c.rng
    shape = smooth(np.asarray(outline, dtype=np.float64), closed=True, samples=6)
    c.wash(
        [shape],
        pigment,
        pigment2=pigment2,
        opacity=0.6,
        edge=0.5,
        flow=0.45,
        gradient=(90, 0.8, 1.2),
        occlude=True,
    )
    c.wash([shape], shade, opacity=0.35, edge=0.2, wet=0.4, gradient=(90, -0.3, 1.0))
    c.drybrush([shape], shade, opacity=0.35, angle=-12, coverage=0.3)
    xs, ys = shape[:, 0], shape[:, 1]
    x_lo, x_hi = float(xs.min()), float(xs.max())
    y_lo, y_hi = float(ys.min()), float(ys.max())
    for _ in range(bushes):
        k = int(rng.integers(0, len(shape)))
        bx, by = float(shape[k, 0]), float(shape[k, 1])
        if by > y_hi - 30:
            continue
        size = float(rng.uniform(14, 30))
        c.wash(
            [blob(bx, by + size * 0.4, size * 1.3, size * 0.7, rng, 0.35)],
            shade,
            pigment2="sap-green",
            opacity=0.55,
            edge=0.6,
            granulation=0.4,
        )
        c.wash(
            [blob(bx, by + size * 0.75, size * 1.1, size * 0.3, rng, 0.3)],
            "indigo",
            opacity=0.25,
            edge=0.4,
        )
    for _ in range(reeds):
        rx = float(rng.uniform(x_lo, x_hi))
        inside = shape[np.abs(shape[:, 0] - rx) < 12]
        if len(inside) == 0:
            continue
        ry = float(inside[:, 1].max()) - float(rng.uniform(4, 30))
        if ry < y_lo + 40:
            continue
        for _ in range(4):
            h = float(rng.uniform(10, 26))
            lean = float(rng.normal(0, 5))
            c.ink(
                [[rx, ry], [rx + lean * 0.4, ry - h * 0.6], [rx + lean, ry - h]],
                width=1.0,
                pigment="hookers-green",
                opacity=0.65,
                taper=0.45,
                jitter=0.25,
            )
