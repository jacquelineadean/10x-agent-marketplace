"""Built things: a stone arch bridge, a timber trestle, a tower crane, roads and buildings."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from chronicle.core.watercolor.canvas import Canvas
from chronicle.core.watercolor.geometry import Points, blob, smooth

Poly = list[list[float]]


def arc(cx: float, cy: float, r: float, a0: float, a1: float, steps: int = 40) -> Poly:
    """Points on a circle from angle a0 to a1 in degrees; 0 is east, 90 is up."""
    out = []
    for a in np.linspace(math.radians(a0), math.radians(a1), steps):
        out.append([cx + r * math.cos(a), cy - r * math.sin(a)])
    return out


def band(cx: float, cy: float, r_in: float, r_out: float, a0: float, a1: float) -> Poly:
    """An annular segment between two radii, as a closed outline."""
    return arc(cx, cy, r_out, a0, a1) + arc(cx, cy, r_in, a1, a0)


def rect(x0: float, y0: float, x1: float, y1: float) -> Poly:
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


@dataclass
class BridgePlan:
    """Where the parts of an arch bridge ended up, so a scene can hang sprites on them."""

    deck: float
    parapet_top: float
    spring: float
    radius: float
    centers: list[float] = field(default_factory=list)
    keystone: Poly = field(default_factory=list)
    keystone_slot: tuple[float, float] = (0.0, 0.0)
    built_right: float = 0.0


def arch_bridge(
    c: Canvas,
    x0: float,
    x1: float,
    spring: float,
    water: float,
    arches: int = 5,
    built: float = 5.0,
    stone: str = "yellow-ochre",
    stone2: str = "raw-sienna",
    shadow: str = "paynes-grey",
    sketch_unbuilt: bool = True,
    detail: float = 1.0,
    piers: bool = True,
) -> BridgePlan:
    """A masonry arch bridge seen side-on.

    `built` counts finished arches; a fraction leaves the next arch on its timber
    centering with the keystone missing. Unbuilt arches are drawn as pencil
    construction lines when `sketch_unbuilt` is set. `piers=False` leaves the piers of
    unbuilt arches as pencil outlines too, for a bridge that exists only on paper.
    """
    n = max(1, arches)
    built = min(max(built, 0.0), float(n))
    pier_w = (x1 - x0) / (n * 5.2)
    span = (x1 - x0 - (n + 1) * pier_w) / n
    r = span / 2.0
    ring = r * 0.17
    crown = spring - r
    deck = crown - ring - r * 0.1
    parapet_top = deck - r * 0.16
    base = water + 3.0
    full = int(math.floor(built))
    frac = built - full
    pier_x = [x0 + i * (span + pier_w) for i in range(n + 1)]
    centers = [pier_x[i] + pier_w + r for i in range(n)]
    plan = BridgePlan(deck=deck, parapet_top=parapet_top, spring=spring, radius=r, centers=centers)

    body_right = pier_x[full] + pier_w if full > 0 else x0
    plan.built_right = body_right
    openings = [
        arc(centers[i], spring, r, 180, 0)
        + [[centers[i] + r, base + 4], [centers[i] - r, base + 4]]
        for i in range(full)
    ]
    body = rect(x0, parapet_top, body_right, base) if full > 0 else []
    stubs = [rect(pier_x[i], spring + 2, pier_x[i] + pier_w, base) for i in range(full + 1, n + 1)]
    if full == 0:
        stubs.insert(0, rect(pier_x[0], spring + 2, pier_x[0] + pier_w, base))
    if not piers:
        for stub in stubs:
            c.pencil(stub, closed=True)
        stubs = []
    partial: list[Poly] = []
    gap = 4.5
    if frac > 0.02 and full < n:
        reach = min(90.0 - gap, frac * 90.0)
        cx = centers[full]
        partial = [
            band(cx, spring, r, r + ring, 180, 180 - reach),
            band(cx, spring, r, r + ring, reach, 0),
        ]
        plan.keystone_slot = (cx, spring - r - ring / 2)
        plan.keystone = band(cx, spring, r - 1, r + ring + 3, 90 + gap, 90 - gap)
    elif full > 0:
        cx = centers[full - 1]
        plan.keystone_slot = (cx, spring - r - ring / 2)
        plan.keystone = band(cx, spring, r - 1, r + ring + 3, 90 + gap, 90 - gap)

    masonry = ([body] if body else []) + stubs + partial
    if not masonry:
        if sketch_unbuilt:
            for cx in centers:
                c.pencil(arc(cx, spring, r, 180, 0))
                c.pencil(arc(cx, spring, r + ring, 180, 0))
            c.pencil([[x0, parapet_top], [x1, parapet_top]])
        return plan
    c.wash(
        masonry,
        "ink",
        opacity=1.0,
        edge=0.0,
        granulation=0.0,
        flow=0.0,
        wobble_px=0.8,
        holes=openings,
        lift=True,
    )
    c.wash(
        masonry,
        stone,
        pigment2=stone2,
        opacity=0.5,
        edge=0.55,
        granulation=0.6,
        holes=openings,
        blooms=1,
        wobble_px=0.8,
    )
    c.wash(
        masonry,
        "burnt-umber",
        pigment2="olive",
        opacity=0.35,
        edge=0.1,
        wet=0.35,
        gradient=(90, -0.2, 1.0),
        holes=openings,
        wobble_px=0.8,
    )

    for i in range(full):
        c.wash(
            [band(centers[i], spring, r, r + ring, 180, 0)],
            stone2,
            opacity=0.3,
            edge=0.4,
            wobble_px=0.5,
        )
        soffit = arc(centers[i], spring, r, 180, 0) + arc(
            centers[i], spring + r * 0.22, r * 0.98, 0, 180
        )
        c.wash([soffit], shadow, pigment2="indigo", opacity=0.6, edge=0.3, wet=0.15, wobble_px=0.5)
    piers_drawn = range(n + 1) if full == 0 else range(full + 1 if frac <= 0.02 else full + 2)
    for i in piers_drawn:
        if i > n:
            continue
        px = pier_x[i]
        c.wash(
            [rect(px + pier_w * 0.55, spring, px + pier_w, base)],
            shadow,
            opacity=0.28,
            edge=0.2,
            wet=0.1,
            wobble_px=0.4,
        )
        cut = [[px - 4, base - 4], [px + pier_w / 2, water - 10], [px + pier_w + 4, base - 4]]
        c.wash([cut], stone2, opacity=0.25, edge=0.4)
    if full > 0:
        c.wash(
            [rect(x0, deck, body_right, deck + 7)], shadow, opacity=0.35, edge=0.2, wobble_px=0.4
        )

    _bridge_ink(c, plan, pier_x, pier_w, full, frac, ring, base, detail)
    if frac > 0.02 and full < n:
        _centering(c, centers[full], spring, r, base)
        _scaffold(c, pier_x[full] - 6, pier_x[full + 1] + pier_w + 6, parapet_top - 10, base, 4)
    if sketch_unbuilt:
        start = full + (1 if frac > 0.02 else 0)
        for i in range(start, n):
            c.pencil(arc(centers[i], spring, r, 180, 0))
            c.pencil(arc(centers[i], spring, r + ring, 180, 0))
        if start < n:
            c.pencil([[body_right, parapet_top], [x1, parapet_top]])
            c.pencil([[body_right, deck], [x1, deck]])
    return plan


def _bridge_ink(
    c: Canvas,
    plan: BridgePlan,
    pier_x: list[float],
    pier_w: float,
    full: int,
    frac: float,
    ring: float,
    base: float,
    detail: float,
) -> None:
    r = plan.radius
    spring = plan.spring
    rng = c.rng
    for i in range(full + (1 if frac > 0.02 else 0)):
        cx = plan.centers[i]
        limit = 90.0 if i < full else min(85.5, frac * 90.0)
        spans = [(180.0, 0.0)] if i < full else [(180.0, 180.0 - limit), (limit, 0.0)]
        for a0, a1 in spans:
            c.ink(arc(cx, spring, r, a0, a1), width=1.5, opacity=0.85)
            c.ink(arc(cx, spring, r + ring, a0, a1), width=1.0, opacity=0.6, breaks=0.25)
            lo, hi = min(a0, a1), max(a0, a1)
            step = 7.5 / max(detail, 0.3)
            for a in np.arange(lo + step / 2, hi, step):
                if i < full and abs(a - 90.0) < 4:
                    continue
                rad = math.radians(float(a))
                c.ink(
                    [
                        [cx + r * math.cos(rad), spring - r * math.sin(rad)],
                        [cx + (r + ring) * math.cos(rad), spring - (r + ring) * math.sin(rad)],
                    ],
                    width=0.8,
                    opacity=0.55,
                    taper=0.3,
                    jitter=0.2,
                )
        if i < full:
            key = band(cx, spring, r - 1, r + ring + 3, 94.5, 85.5)
            c.wash([key], "burnt-sienna", opacity=0.4, edge=0.6, wobble_px=0.3)
            c.ink(key, width=1.2, opacity=0.9, closed=True, jitter=0.2)
    if full > 0:
        right = pier_x[full] + pier_w
        c.ink([[pier_x[0], plan.parapet_top], [right, plan.parapet_top]], width=1.6, opacity=0.85)
        c.ink([[pier_x[0], plan.deck], [right, plan.deck]], width=1.1, opacity=0.7, breaks=0.15)
        courses = int(6 * detail)
        for _ in range(courses * full):
            y = float(rng.uniform(plan.parapet_top + 10, base - 10))
            x = float(rng.uniform(pier_x[0], right - 40))
            length = float(rng.uniform(20, 70))
            c.ink([[x, y], [x + length, y]], width=0.7, opacity=0.35, breaks=0.3, taper=0.3)
        for _ in range(int(7 * detail * full)):
            bx = float(rng.uniform(pier_x[0], right - 16))
            by = float(rng.uniform(plan.parapet_top + 6, base - 8))
            c.wash(
                [rect(bx, by, bx + float(rng.uniform(10, 18)), by + float(rng.uniform(5, 8)))],
                str(rng.choice(["burnt-sienna", "raw-sienna", "warm-grey"])),
                opacity=0.16,
                edge=0.6,
                wobble_px=0.4,
            )
    for i in range(len(pier_x)):
        px = pier_x[i]
        c.ink([[px, spring + 2], [px, base]], width=1.0, opacity=0.6, breaks=0.2)
        c.ink([[px + pier_w, spring + 2], [px + pier_w, base]], width=1.0, opacity=0.6, breaks=0.2)


def _centering(c: Canvas, cx: float, spring: float, r: float, base: float) -> None:
    """Timber formwork that holds an arch until its keystone locks it."""
    timber = "burnt-umber"
    inner = r - 3
    c.wash([band(cx, spring, inner - 9, inner, 180, 0)], "raw-sienna", opacity=0.45, edge=0.5)
    c.ink(arc(cx, spring, inner, 180, 0), width=2.2, pigment=timber, opacity=0.9)
    c.ink(arc(cx, spring, inner - 9, 180, 0), width=1.2, pigment=timber, opacity=0.8)
    c.ink([[cx - inner, spring], [cx + inner, spring]], width=2.4, pigment=timber, opacity=0.9)
    for a in np.linspace(20, 160, 7):
        rad = math.radians(float(a))
        c.ink(
            [
                [cx, spring],
                [cx + (inner - 9) * math.cos(rad), spring - (inner - 9) * math.sin(rad)],
            ],
            width=1.4,
            pigment=timber,
            opacity=0.8,
        )
    for dx in (-0.6, 0.0, 0.6):
        c.ink(
            [[cx + dx * inner, spring], [cx + dx * inner, base]],
            width=2.0,
            pigment=timber,
            opacity=0.85,
        )
    c.ink([[cx - inner * 0.6, spring + 4], [cx, base - 6]], width=1.2, pigment=timber, opacity=0.7)
    c.ink([[cx + inner * 0.6, spring + 4], [cx, base - 6]], width=1.2, pigment=timber, opacity=0.7)


def _scaffold(c: Canvas, x0: float, x1: float, top: float, base: float, levels: int) -> None:
    poles = np.linspace(x0, x1, 4)
    for x in poles:
        c.ink(
            [[float(x), top], [float(x), base]],
            width=1.1,
            pigment="sepia",
            opacity=0.75,
            jitter=0.4,
        )
    for k in range(levels):
        y = top + (base - top) * (k + 0.3) / levels
        c.ink([[x0 - 4, y], [x1 + 4, y]], width=1.0, pigment="sepia", opacity=0.7, jitter=0.4)
        c.wash([rect(x0, y - 3, x1, y)], "yellow-ochre", opacity=0.4, edge=0.5, wobble_px=0.5)
    c.ink(
        [[float(poles[0]), base], [float(poles[1]), top]], width=0.8, pigment="sepia", opacity=0.5
    )
    c.ink(
        [[float(poles[2]), base], [float(poles[3]), top]], width=0.8, pigment="sepia", opacity=0.5
    )


def trestle(
    c: Canvas,
    x0: float,
    x1: float,
    deck: float,
    ground: float,
    bents: int = 12,
    sag: float = 8.0,
    timber: str = "burnt-umber",
    patch: float | None = None,
    strength: float = 1.0,
) -> None:
    """An old timber trestle: a sagging deck on braced bents.

    `patch` is a 0-1 position along the deck where a red emergency brace was added.
    `strength` below 1 fades the whole structure into the distance.
    """
    k_ = strength

    def deck_y(x: float) -> float:
        return deck + sag * math.sin(math.pi * (x - x0) / max(x1 - x0, 1.0))

    xs = np.linspace(x0, x1, 60)
    top = [[float(x), deck_y(float(x))] for x in xs]
    bottom = [[float(x), deck_y(float(x)) + 9] for x in xs[::-1]]
    c.wash([top + bottom], timber, opacity=0.55 * k_, edge=0.5, wobble_px=0.6)
    c.ink(top, width=1.4, opacity=0.85 * k_)
    c.ink([[p[0], p[1] + 9] for p in top], width=1.0, opacity=0.7 * k_)
    c.ink([[p[0], p[1] - 9] for p in top], width=0.8, opacity=0.6 * k_, breaks=0.2)
    for x in np.linspace(x0, x1, 40):
        c.ink(
            [[float(x), deck_y(float(x)) - 9], [float(x), deck_y(float(x))]],
            width=0.6,
            opacity=0.5 * k_,
        )
    bent_x = np.linspace(x0 + 10, x1 - 10, bents)
    for k, raw_x in enumerate(bent_x):
        bx = float(raw_x)
        y = deck_y(bx) + 9
        spread = (ground - y) * 0.18
        c.ink([[bx - 3, y], [bx - spread, ground]], width=1.3, pigment="sepia", opacity=0.8 * k_)
        c.ink([[bx + 3, y], [bx + spread, ground]], width=1.3, pigment="sepia", opacity=0.8 * k_)
        if k + 1 < len(bent_x):
            nx = float(bent_x[k + 1])
            mid = (ground + y) / 2
            c.ink([[bx, y + 4], [nx, mid]], width=0.7, pigment="sepia", opacity=0.5 * k_)
            c.ink([[bx, mid], [nx, y + 4]], width=0.7, pigment="sepia", opacity=0.5 * k_)
            c.ink([[bx, mid], [nx, mid]], width=0.7, pigment="sepia", opacity=0.45 * k_)
    c.wash(
        [[[x0, ground - 4], [x1, ground - 4], [x1, ground + 3], [x0, ground + 3]]],
        "indigo",
        opacity=0.2 * k_,
        wet=0.5,
        edge=0.0,
    )
    if patch is not None:
        px = x0 + (x1 - x0) * patch
        y = deck_y(px) + 9
        c.ink(
            [[px - 22, y + 2], [px + 22, ground - 6]],
            width=2.2,
            pigment="vermilion",
            opacity=0.9 * k_,
        )
        c.ink(
            [[px + 22, y + 2], [px - 22, ground - 6]],
            width=2.2,
            pigment="vermilion",
            opacity=0.9 * k_,
        )


@dataclass
class CranePlan:
    """The crane's hook point, for a cable or a load drawn as a separate layer."""

    hook: tuple[float, float]
    jib_y: float


def crane(
    c: Canvas,
    x: float,
    base: float,
    height: float,
    jib: float = 300.0,
    counter: float = 100.0,
    trolley: float = 0.7,
    paint: str = "cadmium-orange",
) -> CranePlan:
    """A lattice tower crane; `trolley` is how far along the jib the hook hangs (0-1)."""
    top = base - height
    mast = 12.0
    c.wash(
        [rect(x - mast / 2, top, x + mast / 2, base)],
        paint,
        pigment2="gamboge",
        opacity=0.55,
        edge=0.5,
        wobble_px=0.4,
    )
    for side in (-mast / 2, mast / 2):
        c.ink([[x + side, top], [x + side, base]], width=1.1, opacity=0.85, jitter=0.3)
    ys = np.arange(top, base, mast)
    for k, y in enumerate(ys):
        a = -mast / 2 if k % 2 else mast / 2
        c.ink([[x + a, float(y)], [x - a, float(y) + mast]], width=0.6, opacity=0.6, jitter=0.1)
    jib_y = top + 4
    tip = x - jib
    chord = [[x, jib_y - 5], [tip, jib_y]]
    under = [[x, jib_y + 6], [tip, jib_y + 3]]
    c.wash([[chord[0], chord[1], under[1], under[0]]], paint, opacity=0.5, edge=0.5, wobble_px=0.3)
    c.ink(chord, width=1.1, opacity=0.85, jitter=0.3)
    c.ink(under, width=1.0, opacity=0.8, jitter=0.3)
    for k, t in enumerate(np.linspace(0, 1, 26)[:-1]):
        t2 = t + 1 / 25
        xa = x + (tip - x) * float(t)
        xb = x + (tip - x) * float(t2)
        ya_top = jib_y - 5 + 5 * float(t)
        yb_bot = jib_y + 6 - 3 * float(t2)
        if k % 2:
            c.ink([[xa, ya_top], [xb, yb_bot]], width=0.5, opacity=0.55, jitter=0.1)
        else:
            c.ink([[xa, yb_bot + 0], [xb, ya_top]], width=0.5, opacity=0.55, jitter=0.1)
    back = x + counter
    c.ink([[x, jib_y - 3], [back, jib_y - 3]], width=1.2, opacity=0.85)
    c.ink([[x, jib_y + 5], [back, jib_y + 5]], width=1.0, opacity=0.8)
    c.wash([rect(back - 34, jib_y - 2, back - 4, jib_y + 22)], "paynes-grey", opacity=0.6, edge=0.6)
    c.ink(rect(back - 34, jib_y - 2, back - 4, jib_y + 22), width=0.9, opacity=0.8, closed=True)
    apex = [x, top - 42]
    c.ink([[x - mast / 2, top], apex, [x + mast / 2, top]], width=1.2, opacity=0.85)
    c.ink([apex, [tip + jib * 0.3, jib_y - 4]], width=0.7, opacity=0.7, jitter=0.2)
    c.ink([apex, [back - 10, jib_y - 3]], width=0.7, opacity=0.7, jitter=0.2)
    cab = rect(x + mast / 2, jib_y + 6, x + mast / 2 + 16, jib_y + 22)
    c.wash([cab], "gamboge", opacity=0.6, edge=0.6)
    c.ink(cab, width=0.9, opacity=0.85, closed=True)
    hook_x = x + (tip - x) * trolley
    trolley_box = rect(hook_x - 6, jib_y + 4, hook_x + 6, jib_y + 10)
    c.wash([trolley_box], "paynes-grey", opacity=0.6, edge=0.5)
    return CranePlan(hook=(hook_x, jib_y + 10), jib_y=jib_y)


def road(
    c: Canvas,
    center: list[list[float]],
    near: float,
    far: float,
    pigment: str = "yellow-ochre",
    pigment2: str | None = "raw-sienna",
    horizon: float | None = None,
) -> list[tuple[float, float, float]]:
    """A road along a centerline from near (first point) to far, narrowing with distance.

    With `horizon` set, width follows perspective: proportional to the distance below the
    horizon line. Returns (x, y, half width) samples so markers can stand beside it.
    """
    line: Points = smooth(np.asarray(center, dtype=np.float64), closed=False, samples=10)
    n = len(line)
    if horizon is not None:
        depth = np.clip((line[:, 1] - horizon) / max(float(line[0, 1]) - horizon, 1.0), 0.0, 1.0)
        widths = (far + (near - far) * depth) / 2.0
    else:
        widths = np.linspace(near, far, n) / 2.0
    left: Poly = []
    right: Poly = []
    samples: list[tuple[float, float, float]] = []
    for i in range(n):
        a = line[max(i - 1, 0)]
        b = line[min(i + 1, n - 1)]
        tx, ty = b[0] - a[0], b[1] - a[1]
        norm = math.hypot(tx, ty) or 1.0
        nx, ny = -ty / norm, tx / norm
        w = float(widths[i])
        left.append([float(line[i, 0] + nx * w), float(line[i, 1] + ny * w)])
        right.append([float(line[i, 0] - nx * w), float(line[i, 1] - ny * w)])
        samples.append((float(line[i, 0]), float(line[i, 1]), w))
    outline = left + right[::-1]
    c.wash(
        [outline],
        pigment,
        pigment2=pigment2,
        opacity=0.55,
        edge=0.45,
        gradient=(90, 0.5, 1.0),
        granulation=0.6,
        occlude=True,
    )
    for side in (0.45, -0.45):
        rut = [
            [x + (lx - x) * side * 2 * 0.5, y + (ly - y) * side * 2 * 0.5]
            for (x, y, _), (lx, ly) in zip(samples, left, strict=True)
        ]
        c.ink(rut, width=1.1, pigment="burnt-umber", opacity=0.35, breaks=0.35, taper=0.3)
    c.drybrush([outline], "burnt-umber", opacity=0.25, angle=-70, coverage=0.25)
    c.ink(left, width=1.0, opacity=0.6, breaks=0.3)
    c.ink(right, width=1.0, opacity=0.6, breaks=0.3)
    return samples


def milestone(c: Canvas, x: float, ground: float, size: float = 18.0) -> Poly:
    """A surveyor's marker: a stake with a pennant over a cairn; returns the pennant outline."""
    pole_top = ground - size * 2.2
    cairn = blob(x, ground - size * 0.12, size * 0.38, size * 0.2, c.rng, 0.25)
    c.wash(
        [cairn],
        "warm-grey",
        pigment2="lavender",
        opacity=0.6,
        edge=0.6,
        granulation=0.6,
        occlude=True,
    )
    c.ink(
        [[x, ground - size * 0.1], [x, pole_top]],
        width=max(0.9, size * 0.06),
        pigment="sepia",
        opacity=0.9,
        jitter=0.2,
    )
    flag = [[x, pole_top], [x + size * 0.85, pole_top + size * 0.28], [x, pole_top + size * 0.55]]
    c.wash(
        [flag],
        "vermilion",
        pigment2="cadmium-orange",
        opacity=0.8,
        edge=0.6,
        occlude=True,
        wobble_px=0.4,
    )
    c.ink(flag, width=0.8, opacity=0.7, closed=True, jitter=0.2)
    c.wash(
        [
            [
                [x - size * 0.6, ground - 1],
                [x + size * 0.9, ground - 1],
                [x + size * 0.8, ground + 3],
                [x - size * 0.5, ground + 3],
            ]
        ],
        "indigo",
        opacity=0.25,
        wet=0.5,
        edge=0.0,
    )
    return flag


def buildings(
    c: Canvas,
    x0: float,
    x1: float,
    base: float,
    tallest: float,
    count: int = 8,
    palette: tuple[str, ...] = ("warm-grey", "raw-sienna", "lavender", "cerulean"),
    windows: bool = True,
) -> None:
    """A skyline of towers between x0 and x1; `count` sets how many, roughly."""
    rng = c.rng
    mean_w = (x1 - x0) / max(count, 1)
    x = x0
    k = 0
    while x < x1 - 10:
        width = min(float(rng.uniform(0.55, 1.25)) * mean_w, x1 - x)
        left, right = x + 1.5, x + width - 1.5
        x += width + float(rng.uniform(-0.15, 0.25)) * mean_w
        if right - left < 12:
            continue
        height = tallest * float(rng.uniform(0.35, 1.0)) ** 1.3
        shape = rect(left, base - height, right, base)
        c.wash(
            [shape],
            palette[k % len(palette)],
            opacity=0.5,
            edge=0.55,
            gradient=(90, 1.0, 0.7),
            occlude=True,
        )
        c.wash(
            [rect(right - (right - left) * 0.32, base - height, right, base)],
            "paynes-grey",
            opacity=0.22,
            edge=0.3,
        )
        c.ink(shape, width=1.0, opacity=0.75, closed=True, breaks=0.1)
        if rng.random() < 0.3:
            mast = (left + right) / 2
            c.ink(
                [[mast, base - height], [mast, base - height - tallest * 0.08]],
                width=0.8,
                opacity=0.7,
            )
        if windows:
            for wy in np.arange(base - height + 10, base - 12, 13):
                for wx in np.arange(left + 5, right - 7, 10):
                    if rng.random() < 0.3:
                        c.wash(
                            [rect(float(wx), float(wy), float(wx) + 4.5, float(wy) + 6.5)],
                            "gamboge",
                            opacity=0.55,
                            edge=0.5,
                            wobble_px=0.2,
                        )
        k += 1


def vehicle(
    c: Canvas, x: float, ground: float, length: float = 34.0, paint: str = "cobalt"
) -> None:
    """A small boxy truck, facing right."""
    h = length * 0.42
    body = rect(x, ground - h, x + length * 0.68, ground - 3)
    cab = [
        [x + length * 0.7, ground - h * 0.72],
        [x + length * 0.92, ground - h * 0.72],
        [x + length, ground - h * 0.35],
        [x + length, ground - 3],
        [x + length * 0.7, ground - 3],
    ]
    c.wash([body], paint, opacity=0.6, edge=0.6, wobble_px=0.3, occlude=True)
    c.wash([cab], "warm-grey", opacity=0.45, edge=0.6, wobble_px=0.3, occlude=True)
    c.ink(body, width=0.8, opacity=0.8, closed=True, jitter=0.2)
    c.ink(cab, width=0.8, opacity=0.8, closed=True, jitter=0.2)
    for wx in (x + length * 0.18, x + length * 0.82):
        wheel = blob(wx, ground - 2, length * 0.09, length * 0.09, c.rng, 0.05)
        c.wash([wheel], "ink", opacity=0.75, edge=0.3, wobble_px=0.0)


def figure(
    c: Canvas,
    x: float,
    ground: float,
    height: float = 16.0,
    coat: str = "vermilion",
    hat: str | None = "gamboge",
) -> None:
    """A tiny standing person, the scale reference every landscape wants."""
    rng = c.rng
    head_r = height * 0.1
    shoulders = ground - height * 0.78
    hips = ground - height * 0.4
    torso = [
        [x - height * 0.12, shoulders],
        [x + height * 0.12, shoulders],
        [x + height * 0.1, hips],
        [x - height * 0.1, hips],
    ]
    c.wash([torso], coat, opacity=0.75, edge=0.6, wobble_px=0.3, occlude=True)
    stride = float(rng.uniform(-0.12, 0.12)) * height
    c.ink(
        [[x - height * 0.05, hips], [x - height * 0.06 - stride, ground]], width=1.1, opacity=0.85
    )
    c.ink(
        [[x + height * 0.05, hips], [x + height * 0.06 + stride, ground]], width=1.1, opacity=0.85
    )
    head = blob(x, shoulders - head_r * 1.3, head_r, head_r * 1.1, rng, 0.05)
    c.wash(
        [head],
        str(rng.choice(["raw-sienna", "burnt-sienna", "burnt-umber"])),
        opacity=0.6,
        edge=0.5,
        wobble_px=0.1,
    )
    if hat:
        c.wash(
            [
                [
                    [x - head_r * 1.2, shoulders - head_r * 1.6],
                    [x + head_r * 1.2, shoulders - head_r * 1.6],
                    [x + head_r * 0.9, shoulders - head_r * 2.6],
                    [x - head_r * 0.9, shoulders - head_r * 2.6],
                ]
            ],
            hat,
            opacity=0.8,
            edge=0.5,
            wobble_px=0.1,
        )
