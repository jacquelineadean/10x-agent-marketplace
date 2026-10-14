"""Composed illustrations with moving layers.

The bridge family tells a build-and-migrate story: an old timber trestle (the system being
replaced) and a new stone arch bridge going up beside it, one arch per milestone. Each
preset takes a few story-level parameters, so a status page can show real progress
(`built=3.75` is three finished arches and a fourth waiting for its keystone).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import numpy as np

from chronicle.core.watercolor.canvas import Canvas
from chronicle.core.watercolor.geometry import blob
from chronicle.core.watercolor.motifs import nature, structures
from chronicle.core.watercolor.scene import Layer, Painting, SceneError

Preset = Callable[[Mapping[str, Any], float], Painting]


def _layer(c: Canvas, name: str, motion: str, travel: float = 0.0) -> Layer | None:
    image, box = c.sprite()
    if box is None:
        return None
    return Layer(name=name, image=image, box=box, motion=motion, travel=travel)


def _valley(
    c: Canvas,
    horizon: float,
    far_water: float,
    mood: str,
    clouds: int = 4,
    snow: bool = False,
) -> None:
    w = c.scene_width
    nature.sky(c, horizon, mood=mood, clouds=clouds, cloud_band=(0.15, 0.5))
    hues = {"storm": ("paynes-grey", "indigo"), "mist": ("warm-grey", "lavender")}
    far, far2 = hues.get(mood, ("lavender", "ultramarine"))
    nature.mountains(c, horizon - 20, horizon * 0.33, far, far2, opacity=0.4, snow=snow, seed=4)
    nature.hills(
        c,
        far_water - 30,
        80,
        "cobalt-teal",
        "lavender",
        opacity=0.32,
        seed=9,
        bottom=far_water + 30,
    )
    nature.treeline(
        c, -20, w + 20, far_water + 4, 30, pigment="viridian", pigment2="lavender", opacity=0.38
    )


def bridge_hero(params: Mapping[str, Any], scale: float) -> Painting:
    """Dawn over the valley: the new bridge with its keystone on the crane hook."""
    w, h = 1800, 820
    seed = int(params.get("seed", 11))
    arches = int(params.get("arches", 5))
    built = float(params.get("built", 3.75))
    mood = str(params.get("mood", "dawn"))
    c = Canvas(w, h, seed=seed, scale=scale)
    nature.sky(c, 520, mood=mood, clouds=4, cloud_band=(0.15, 0.5))
    plan_probe = _bridge_geometry(300, 1600, 600, arches, built)
    nature.sun(c, plan_probe, 318, 30)
    nature.mountains(c, 500, 170, "lavender", "ultramarine", opacity=0.38, seed=4)
    nature.hills(c, 560, 80, "cobalt-teal", "lavender", opacity=0.32, seed=9, bottom=620)
    nature.treeline(c, -20, 1820, 590, 30, pigment="viridian", pigment2="lavender", opacity=0.38)
    nature.water(
        c, [[-20, 586], [w + 20, 586], [w + 20, h + 20], [-20, h + 20]], opacity=0.42, ripples=0
    )
    structures.trestle(c, -20, 1820, 548, 594, bents=30, sag=6, patch=0.47, strength=0.55)
    for x, paint in ((180, "cobalt"), (640, "vermilion"), (1320, "sap-green")):
        structures.vehicle(
            c, x, 548 + 6 * np.sin(np.pi * (x + 20) / 1840) - 0.5, length=20, paint=paint
        )
    plan = structures.arch_bridge(c, 300, 1600, spring=600, water=690, arches=arches, built=built)
    slot_x, slot_y = plan.keystone_slot
    crane_x = min(slot_x + 250, 1560)
    c.wash(
        [[[crane_x - 45, 684], [crane_x + 45, 684], [crane_x + 38, 700], [crane_x - 38, 700]]],
        "paynes-grey",
        opacity=0.7,
        edge=0.5,
    )
    crane = structures.crane(
        c, crane_x, 686, 496, jib=420, counter=130, trolley=(crane_x - slot_x) / 420
    )
    c.reflect(690, 200, strength=0.9)
    c.wash(
        [[[-20, 700], [w + 20, 700], [w + 20, h + 20], [-20, h + 20]]],
        "ultramarine",
        pigment2="paynes-grey",
        opacity=0.35,
        wet=0.6,
        edge=0.0,
        gradient=(90, 0.2, 1.0),
    )
    nature.water(
        c, [[-20, 700], [w + 20, 700], [w + 20, h + 20], [-20, h + 20]], opacity=0.0, ripples=70
    )
    nature.bank(
        c,
        [
            [-30, 420],
            [90, 436],
            [210, 490],
            [300, 560],
            [370, 650],
            [440, 760],
            [520, 850],
            [-30, 850],
        ],
        bushes=8,
    )
    nature.bank(
        c,
        [[1830, 440], [1700, 462], [1600, 530], [1560, 610], [1500, 720], [1440, 850], [1830, 850]],
        bushes=8,
    )
    nature.tree(c, 60, 520, 260)
    nature.tree(c, 175, 560, 150, kind="conifer")
    nature.tree(c, 1740, 575, 220)
    nature.tree(c, 1640, 610, 120, kind="conifer")
    deck_x = plan.built_right - 70
    for dx in (0, 30, 56):
        structures.figure(c, deck_x + dx, plan.parapet_top + 1, 14, coat="vermilion")
    structures.figure(c, slot_x - 90, 640, 13, coat="cadmium-orange")
    painting = Painting(w, h, c.finish("deckle"))

    travel = 150.0
    if plan.keystone and built < arches:
        k = Canvas(w, h, seed=seed + 1, scale=scale, paper=c.paper)
        key = np.asarray(plan.keystone, dtype=np.float64)
        key[:, 1] -= travel
        k.reserve([key])
        k.wash([key], "yellow-ochre", pigment2="raw-sienna", opacity=0.6, edge=0.6, granulation=0.6)
        k.wash([key], "burnt-sienna", opacity=0.25, edge=0.3, gradient=(0, 0.2, 1.0))
        k.ink(key, width=1.3, closed=True)
        top = float(key[:, 1].min())
        mid = float(key[:, 0].mean())
        sling_top = top - 26
        k.ink(
            [
                [float(key[:, 0].min()) + 3, top + 4],
                [mid, sling_top],
                [float(key[:, 0].max()) - 3, top + 4],
            ],
            width=1.0,
        )
        layer = _layer(k, "keystone", "descend", travel)
        if layer:
            painting.layers.append(layer)
        painting.anchors["hook"] = crane.hook
        painting.anchors["load"] = (mid, sling_top)
        painting.anchors["slot"] = (slot_x, slot_y)
    b = Canvas(w, h, seed=seed + 2, scale=scale, paper=c.paper)
    nature.birds(b, 520, 210, count=6, spread=110)
    layer = _layer(b, "birds", "drift", 40)
    if layer:
        painting.layers.append(layer)
    return painting


def _bridge_geometry(x0: float, x1: float, spring: float, arches: int, built: float) -> float:
    """X of the arch that is waiting for its keystone, so the sun can sit behind it."""
    n = max(1, arches)
    pier_w = (x1 - x0) / (n * 5.2)
    span = (x1 - x0 - (n + 1) * pier_w) / n
    index = min(int(built), n - 1)
    return x0 + index * (span + pier_w) + pier_w + span / 2


def bridge_old_crossing(params: Mapping[str, Any], scale: float) -> Painting:
    """The old trestle in morning mist, traffic queued on a deck it was never built for."""
    w, h = 1600, 760
    seed = int(params.get("seed", 21))
    c = Canvas(w, h, seed=seed, scale=scale)
    nature.sky(c, 470, mood="dawn", clouds=2, intensity=0.7)
    c.glow(1180, 400, 260, "gamboge", 0.3)
    nature.mountains(c, 470, 120, "warm-grey", "lavender", opacity=0.32, seed=8)
    nature.treeline(c, -20, w + 20, 524, 22, pigment="viridian", pigment2="lavender", opacity=0.3)
    nature.water(
        c,
        [[-20, 520], [w + 20, 520], [w + 20, h + 20], [-20, h + 20]],
        pigment="paynes-grey",
        pigment2="lavender",
        opacity=0.38,
        ripples=0,
    )
    structures.arch_bridge(c, 260, 1500, spring=520, water=560, arches=5, built=0.0, piers=False)
    c.wash(
        [[[-20, 440], [w + 20, 440], [w + 20, 600], [-20, 600]]],
        "lavender",
        opacity=0.22,
        wet=1.0,
        edge=0.0,
        gradient=(90, 0.0, 1.0),
    )
    structures.trestle(c, -20, w + 20, 330, 640, bents=12, sag=22, patch=0.58)
    lane = [
        (110, "cobalt"),
        (170, "vermilion"),
        (232, "sap-green"),
        (292, "gamboge"),
        (352, "cobalt"),
        (414, "madder"),
        (476, "paynes-grey"),
        (540, "vermilion"),
        (602, "cerulean"),
        (664, "sap-green"),
        (726, "raw-sienna"),
    ]
    for x, paint in lane:
        deck_y = 330 + 22 * np.sin(np.pi * (x + 20) / (w + 40))
        structures.vehicle(c, x, deck_y - 0.5, length=46, paint=paint)
    c.reflect(640, 120, strength=0.85)
    nature.water(
        c,
        [[-20, 642], [w + 20, 642], [w + 20, h + 20], [-20, h + 20]],
        pigment="paynes-grey",
        opacity=0.28,
        ripples=70,
    )
    nature.bank(c, [[-30, 500], [120, 540], [210, 650], [260, 790], [-30, 790]], bushes=4, reeds=12)
    nature.bank(
        c, [[w + 30, 600], [1500, 640], [1450, 700], [1430, 790], [w + 30, 790]], bushes=3, reeds=14
    )
    nature.tree(c, 70, 560, 210, kind="conifer")
    # A load-limit sign at the approach: the old crossing's rules, posted.
    c.ink([[196, 560], [196, 486]], width=2.0, pigment="sepia", opacity=0.9)
    sign = blob(196, 470, 19, 19, c.rng, 0.03)
    c.wash([sign], "vermilion", opacity=0.85, edge=0.6, wobble_px=0.3, occlude=True)
    c.reserve([blob(196, 470, 12, 12, c.rng, 0.03)])
    c.ink([[189, 474], [203, 474]], width=1.6, opacity=0.9)
    c.ink([[189, 467], [203, 467]], width=1.6, opacity=0.9)
    painting = Painting(w, h, c.finish("deckle"))
    painting.anchors["patch"] = (0.58 * (w + 40) - 20, 400)
    painting.anchors["queue"] = (420, 300)
    painting.anchors["sign"] = (196, 450)
    return painting


def bridge_piers(params: Mapping[str, Any], scale: float) -> Painting:
    """Year one: piers rising out of the river inside their cofferdams."""
    w, h = 1600, 760
    seed = int(params.get("seed", 31))
    arches = int(params.get("arches", 5))
    c = Canvas(w, h, seed=seed, scale=scale)
    _valley(c, 470, 540, "day", clouds=3)
    nature.water(
        c, [[-20, 536], [w + 20, 536], [w + 20, h + 20], [-20, h + 20]], opacity=0.45, ripples=0
    )
    structures.trestle(c, -20, w + 20, 500, 544, bents=26, sag=5, strength=0.5)
    x0, x1, water = 220.0, 1400.0, 640.0
    pier_w = (x1 - x0) / (arches * 5.2)
    span = (x1 - x0 - (arches + 1) * pier_w) / arches
    for i in range(arches + 1):
        px = x0 + i * (span + pier_w)
        rise = [150.0, 120.0, 90.0, 60.0, 30.0, 12.0][min(i, 5)]
        top = water - rise
        dam = [
            [px - 26, water - 16],
            [px + pier_w + 26, water - 16],
            [px + pier_w + 26, water + 6],
            [px - 26, water + 6],
        ]
        c.reserve([dam])
        c.wash([dam], "paynes-grey", pigment2="burnt-umber", opacity=0.6, edge=0.6)
        for sx in np.arange(px - 24, px + pier_w + 26, 6):
            c.ink([[float(sx), water - 16], [float(sx), water + 6]], width=0.6, opacity=0.5)
        pier = [[px, top], [px + pier_w, top], [px + pier_w, water - 16], [px, water - 16]]
        c.reserve([pier])
        c.wash(
            [pier], "yellow-ochre", pigment2="raw-sienna", opacity=0.5, edge=0.55, granulation=0.6
        )
        c.wash(
            [
                [
                    [px + pier_w * 0.55, top],
                    [px + pier_w, top],
                    [px + pier_w, water - 16],
                    [px + pier_w * 0.55, water - 16],
                ]
            ],
            "paynes-grey",
            opacity=0.28,
            edge=0.2,
        )
        c.ink(pier, width=1.2, closed=True, opacity=0.85)
        for yy in np.arange(top + 12, water - 18, 12):
            c.ink(
                [[px + 2, float(yy)], [px + pier_w - 2, float(yy)]],
                width=0.6,
                opacity=0.35,
                breaks=0.3,
            )
        if i < 3:
            structures.figure(c, px + pier_w / 2, top + 1, 13, coat="vermilion")
    centre = x0 + 2 * (span + pier_w) + pier_w + span / 2
    c.pencil([[x0, water - 260], [x1 + pier_w, water - 260]])
    for i in range(arches):
        cx = x0 + i * (span + pier_w) + pier_w + span / 2
        pts = [
            [cx + span / 2 * np.cos(a), water - 150 - span / 2 * np.sin(a)]
            for a in np.linspace(np.pi, 0, 30)
        ]
        c.pencil(pts)
    structures.crane(c, x1 + 120, 650, 470, jib=380, counter=110, trolley=0.55)
    c.reflect(640, 160, strength=0.8)
    c.wash(
        [[[-20, 652], [w + 20, 652], [w + 20, h + 20], [-20, h + 20]]],
        "ultramarine",
        pigment2="paynes-grey",
        opacity=0.3,
        wet=0.6,
        edge=0.0,
        gradient=(90, 0.2, 1.0),
    )
    nature.water(
        c, [[-20, 652], [w + 20, 652], [w + 20, h + 20], [-20, h + 20]], opacity=0.0, ripples=60
    )
    nature.bank(
        c, [[-30, 470], [80, 500], [160, 580], [200, 700], [230, 800], [-30, 800]], bushes=5
    )
    nature.tree(c, 60, 520, 200)
    painting = Painting(w, h, c.finish("deckle"))
    painting.anchors["centre"] = (centre, water - 150)
    return painting


def bridge_flood(params: Mapping[str, Any], scale: float) -> Painting:
    """The storm: the river up at the springing line, rain driving across the half-built span."""
    w, h = 1600, 760
    seed = int(params.get("seed", 41))
    built = float(params.get("built", 2.6))
    arches = int(params.get("arches", 5))
    c = Canvas(w, h, seed=seed, scale=scale)
    nature.sky(c, 470, mood="storm", clouds=4, cloud_band=(0.1, 0.45))
    nature.mountains(c, 470, 130, "paynes-grey", "indigo", opacity=0.5, seed=4)
    nature.water(
        c,
        [[-20, 520], [w + 20, 520], [w + 20, h + 20], [-20, h + 20]],
        pigment="burnt-umber",
        pigment2="paynes-grey",
        opacity=0.5,
        ripples=0,
    )
    structures.trestle(c, -20, w + 20, 470, 530, bents=24, sag=10, patch=0.4, strength=0.6)
    plan = structures.arch_bridge(
        c,
        200,
        1400,
        spring=560,
        water=600,
        arches=arches,
        built=built,
        stone="raw-sienna",
        stone2="burnt-umber",
        shadow="indigo",
    )
    c.reflect(600, 120, strength=0.6)
    flood = [[-20, 604], [w + 20, 604], [w + 20, h + 20], [-20, h + 20]]
    c.wash(
        [flood],
        "burnt-umber",
        pigment2="olive",
        opacity=0.55,
        edge=0.2,
        wet=0.3,
        flow=0.7,
        blooms=3,
        gradient=(90, 0.5, 1.0),
    )
    rng = c.rng
    for _ in range(70):
        x = float(rng.uniform(-20, w))
        y = float(rng.uniform(610, h))
        ln = float(rng.uniform(30, 120))
        c.reserve([[[x, y], [x + ln, y - 2], [x + ln * 0.9, y + 2.5], [x, y + 3]]], softness=0.2)
    nature.bank(
        c,
        [[-30, 500], [90, 540], [150, 640], [190, 800], [-30, 800]],
        bushes=4,
        pigment="olive",
        pigment2="paynes-grey",
    )
    nature.tree(c, 60, 540, 220, kind="conifer", pigment="hookers-green", shade="indigo")
    painting = Painting(w, h, c.finish("deckle"))
    rain = Canvas(w, h, seed=seed + 3, scale=scale, paper=c.paper)
    nature.rain(rain, count=520, angle=16, length=(22, 60), opacity=0.4)
    layer = _layer(rain, "rain", "fall", 60)
    if layer:
        painting.layers.append(layer)
    painting.anchors["centering"] = (plan.keystone_slot[0], plan.spring - plan.radius / 2)
    return painting


def bridge_span(params: Mapping[str, Any], scale: float) -> Painting:
    """Midday: four arches carry traffic while the old trestle comes down behind them."""
    w, h = 1800, 760
    seed = int(params.get("seed", 51))
    built = float(params.get("built", 4.0))
    arches = int(params.get("arches", 5))
    c = Canvas(w, h, seed=seed, scale=scale)
    _valley(c, 480, 540, "day", clouds=5)
    nature.water(
        c, [[-20, 536], [w + 20, 536], [w + 20, h + 20], [-20, h + 20]], opacity=0.42, ripples=0
    )
    structures.trestle(c, 760, w + 20, 500, 544, bents=16, sag=4, strength=0.45)
    for x in np.linspace(-20, 740, 14):
        c.pencil([[float(x), 500], [float(x) + 14, 544]], opacity=0.3)
    plan = structures.arch_bridge(c, 240, 1540, spring=580, water=660, arches=arches, built=built)
    c.reflect(660, 200, strength=0.9)
    c.wash(
        [[[-20, 670], [w + 20, 670], [w + 20, h + 20], [-20, h + 20]]],
        "ultramarine",
        pigment2="paynes-grey",
        opacity=0.3,
        wet=0.6,
        edge=0.0,
        gradient=(90, 0.2, 1.0),
    )
    nature.water(
        c, [[-20, 670], [w + 20, 670], [w + 20, h + 20], [-20, h + 20]], opacity=0.0, ripples=70
    )
    nature.bank(
        c, [[-30, 430], [120, 450], [220, 520], [280, 610], [330, 720], [380, 800], [-30, 800]]
    )
    nature.bank(c, [[1830, 450], [1690, 480], [1590, 560], [1540, 660], [1500, 800], [1830, 800]])
    nature.tree(c, 80, 470, 230)
    nature.tree(c, 1730, 520, 200)
    nature.tree(c, 1640, 560, 130, kind="conifer")
    for walker_x in (420, 700, 980):
        structures.figure(
            c,
            walker_x,
            plan.parapet_top + 1,
            14,
            coat=str(c.rng.choice(["cobalt", "vermilion", "sap-green"])),
        )
    painting = Painting(w, h, c.finish("deckle"))
    traffic = Canvas(w, h, seed=seed + 4, scale=scale, paper=c.paper)
    for k, paint in enumerate(("cobalt", "vermilion", "gamboge", "sap-green")):
        structures.vehicle(traffic, 260 + k * 70, plan.parapet_top - 0.5, length=34, paint=paint)
    layer = _layer(traffic, "traffic", "cross", plan.built_right - 560)
    if layer:
        painting.layers.append(layer)
    return painting


def road_ahead(params: Mapping[str, Any], scale: float) -> Painting:
    """From the far bank: the road runs toward the mountains past one milestone per step."""
    w, h = 1800, 820
    seed = int(params.get("seed", 61))
    stops = int(params.get("milestones", 4))
    c = Canvas(w, h, seed=seed, scale=scale)
    nature.sky(c, 450, mood=str(params.get("mood", "dusk")), clouds=3, cloud_band=(0.15, 0.55))
    nature.sun(c, 1060, 380, 26, pigment="cadmium-orange")
    nature.mountains(c, 450, 200, "lavender", "ultramarine", opacity=0.48, seed=12)
    nature.hills(c, 520, 70, "cobalt-teal", "lavender", opacity=0.35, seed=5, bottom=580)
    meadow = [[-20, 540], [w + 20, 540], [w + 20, h + 20], [-20, h + 20]]
    c.wash(
        [meadow],
        "sap-green",
        pigment2="yellow-ochre",
        opacity=0.5,
        edge=0.3,
        flow=0.5,
        gradient=(90, 0.55, 1.2),
    )
    c.wash([meadow], "hookers-green", opacity=0.3, wet=0.5, edge=0.0, gradient=(90, -0.4, 1.0))
    c.drybrush([meadow], "olive", opacity=0.3, angle=-4, coverage=0.25)
    nature.treeline(c, -20, 760, 552, 22, pigment="viridian", pigment2="lavender", opacity=0.35)
    nature.treeline(c, 1300, w + 20, 556, 26, pigment="viridian", pigment2="lavender", opacity=0.35)
    centre: list[list[float]] = [
        [600, h + 40],
        [800, 750],
        [980, 668],
        [1040, 610],
        [1052, 570],
        [1060, 545],
    ]
    samples = structures.road(c, centre, near=340, far=4, horizon=538)
    anchors: dict[str, tuple[float, float]] = {}
    ys = np.array([sample[1] for sample in samples])
    depths = np.linspace(0.78, 0.1, stops)
    picks = [int(np.argmin(np.abs(ys - (538 + d * (h + 40 - 538))))) for d in depths]
    for k, idx in enumerate(picks):
        x, y, half = samples[idx]
        depth = (y - 540) / (h - 540)
        size = 9 + 36 * depth
        side = -1 if k % 2 == 0 else 1
        mx = x + side * (half + size * 0.9)
        structures.milestone(c, mx, y + size * 0.1, size=size)
        anchors[f"m{k + 1}"] = (mx, y + size * 0.1 - size)
    for x, ground, height in (
        (1150, 600, 70),
        (1190, 640, 110),
        (1250, 700, 170),
        (1340, 790, 260),
    ):
        nature.tree(c, x, ground, height, kind="poplar")
    for x, ground, height in ((110, 800, 330), (300, 810, 170)):
        nature.tree(c, x, ground, height, kind="round" if height > 200 else "conifer")
    nature.tree(c, 1650, 820, 300)
    painting = Painting(w, h, c.finish("deckle"))
    painting.anchors.update(anchors)
    b = Canvas(w, h, seed=seed + 5, scale=scale, paper=c.paper)
    nature.birds(b, 1280, 220, count=5, spread=90)
    layer = _layer(b, "birds", "drift", 50)
    if layer:
        painting.layers.append(layer)
    return painting


def keystone_spot(params: Mapping[str, Any], scale: float) -> Painting:
    """A small vignette of one arch whose keystone is the only stone in full colour."""
    w, h = 460, 340
    c = Canvas(w, h, seed=int(params.get("seed", 71)), scale=scale)
    cx, spring, r, ring = 230.0, 270.0, 120.0, 46.0
    c.wash([blob(cx, spring + 30, 210, 20, c.rng, 0.2)], "lavender", opacity=0.3, wet=0.7, edge=0.0)
    count = 13
    for k in range(count):
        a0 = 180.0 - k * 180.0 / count
        a1 = a0 - 180.0 / count
        stone = structures.band(cx, spring, r, r + ring, a0 - 0.8, a1 + 0.8)
        key = k == count // 2
        c.wash(
            [stone],
            "burnt-sienna" if key else "warm-grey",
            pigment2="raw-sienna" if key else "yellow-ochre",
            opacity=0.75 if key else 0.28,
            edge=0.6,
            granulation=0.6,
            wobble_px=0.6,
        )
        c.ink(
            stone, width=1.6 if key else 0.9, closed=True, opacity=0.9 if key else 0.55, jitter=0.4
        )
    for side in (-1, 1):
        px = cx + side * (r + ring / 2)
        pier = structures.rect(px - ring / 2, spring, px + ring / 2, spring + 46)
        c.wash([pier], "warm-grey", opacity=0.25, edge=0.5)
        c.ink(pier, width=0.9, opacity=0.5, closed=True, breaks=0.2)
    c.splatter(cx + 120, 70, 40, 10, "burnt-sienna")
    return Painting(w, h, c.finish("spot"))


def valley(params: Mapping[str, Any], scale: float) -> Painting:
    """A generic river valley in any weather; a backdrop for chapters without a set scene."""
    w, h = int(params.get("width", 1600)), int(params.get("height", 700))
    mood = str(params.get("mood", "day"))
    c = Canvas(w, h, seed=int(params.get("seed", 81)), scale=scale)
    horizon = h * 0.62
    nature.sky(c, horizon, mood=mood, clouds=int(params.get("clouds", 4)))
    if mood in ("dawn", "dusk"):
        nature.sun(c, w * 0.68, horizon * 0.62, h * 0.04, pigment="cadmium-orange")
    nature.mountains(c, horizon, h * 0.24, "lavender", "ultramarine", opacity=0.45, seed=3)
    nature.hills(
        c,
        horizon + h * 0.06,
        h * 0.1,
        "cobalt-teal",
        "lavender",
        opacity=0.35,
        seed=6,
        bottom=horizon + h * 0.16,
    )
    water_y = horizon + h * 0.12
    nature.water(
        c,
        [[-20, water_y], [w + 20, water_y], [w + 20, h + 20], [-20, h + 20]],
        opacity=0.4,
        ripples=50,
    )
    c.reflect(water_y, h * 0.2, strength=0.6)
    nature.bank(
        c,
        [
            [-30, horizon - h * 0.02],
            [w * 0.12, horizon + h * 0.04],
            [w * 0.2, horizon + h * 0.2],
            [w * 0.26, h + 30],
            [-30, h + 30],
        ],
        bushes=5,
    )
    nature.bank(
        c,
        [
            [w + 30, horizon + h * 0.02],
            [w * 0.86, horizon + h * 0.08],
            [w * 0.78, horizon + h * 0.24],
            [w * 0.74, h + 30],
            [w + 30, h + 30],
        ],
        bushes=5,
    )
    nature.tree(c, w * 0.06, horizon + h * 0.12, h * 0.36)
    nature.tree(c, w * 0.93, horizon + h * 0.16, h * 0.3, kind="conifer")
    painting = Painting(w, h, c.finish("deckle"))
    b = Canvas(w, h, seed=int(params.get("seed", 81)) + 1, scale=scale, paper=c.paper)
    nature.birds(b, w * 0.4, h * 0.22, count=5, spread=w * 0.06)
    layer = _layer(b, "birds", "drift", 40)
    if layer:
        painting.layers.append(layer)
    return painting


def waterfront(params: Mapping[str, Any], scale: float) -> Painting:
    """A city waterfront at dusk: towers, lit windows and their reflections."""
    w, h = int(params.get("width", 1600)), int(params.get("height", 700))
    c = Canvas(w, h, seed=int(params.get("seed", 91)), scale=scale)
    shore = h * 0.66
    nature.sky(c, shore, mood=str(params.get("mood", "dusk")), clouds=3)
    structures.buildings(
        c,
        w * 0.02,
        w * 0.98,
        shore - h * 0.02,
        h * 0.44,
        count=int(params.get("towers", 16)),
        palette=("lavender", "warm-grey", "cerulean", "paynes-grey"),
    )
    structures.buildings(
        c,
        w * 0.04,
        w * 0.96,
        shore,
        h * 0.22,
        count=14,
        palette=("burnt-sienna", "yellow-ochre", "raw-sienna", "warm-grey"),
    )
    nature.water(
        c,
        [[-20, shore], [w + 20, shore], [w + 20, h + 20], [-20, h + 20]],
        pigment="ultramarine",
        opacity=0.45,
        ripples=70,
    )
    c.reflect(shore, h * 0.3, strength=0.8)
    c.wash(
        [[[-20, shore - 4], [w + 20, shore - 4], [w + 20, shore + 6], [-20, shore + 6]]],
        "paynes-grey",
        opacity=0.6,
        edge=0.4,
    )
    return Painting(w, h, c.finish("deckle"))


PRESETS: dict[str, Preset] = {
    "bridge-hero": bridge_hero,
    "bridge-old-crossing": bridge_old_crossing,
    "bridge-piers": bridge_piers,
    "bridge-flood": bridge_flood,
    "bridge-span": bridge_span,
    "road-ahead": road_ahead,
    "keystone-spot": keystone_spot,
    "valley": valley,
    "waterfront": waterfront,
}


def paint_preset(name: str, params: Mapping[str, Any], scale: float = 1.0) -> Painting:
    """Paint a named preset; unknown names list the choices."""
    if name not in PRESETS:
        raise SceneError(f"unknown preset {name!r}; use one of: {', '.join(PRESETS)}")
    return PRESETS[name](params, scale)
