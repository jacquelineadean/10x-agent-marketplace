"""Lines between TAD components: square routes with round corners through the gutters.

An edge leaves the side of its node that faces its target and enters the side that
faces its source. Where several edges share a side, their ends spread along it, sorted
by where the other end is, so they do not cross at the box. A route runs straight when
nothing is in the way, else bends in a gutter between tiers, else drops into a channel
between lanes. Lines that share a gutter get their own tracks, ten pixels apart.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from chronicle.core.motion.tad.layout import Layout, Rect
from chronicle.core.motion.tad.spec import Edge, Tad

Pt = tuple[float, float]
RADIUS = 10.0
HEAD = 9.0  # arrowhead length
CLEAR = 7.0  # space kept between a line and a box it passes
TRACK = 10.0


@dataclass
class Route:
    """One edge's geometry in frame coordinates of the diagram."""

    edge: Edge
    points: list[Pt]
    line: str = ""  # path data for the drawn line, short of its arrowheads
    full: str = ""  # path data end to end, for packets
    length: float = 0.0
    line_length: float = 0.0
    heads: list[str] = field(default_factory=list)
    label: tuple[float, float, str] | None = None


def route_all(tad: Tad, layout: Layout) -> dict[str, Route]:
    """Route every edge; returns routes by edge id."""
    sides = _sides(tad, layout)
    ports = _ports(tad, layout, sides)
    routes: dict[str, Route] = {}
    for edge in tad.edges.values():
        pts = _route(edge, layout, sides[edge.id], ports)
        routes[edge.id] = Route(edge, pts)
    _tracks(routes, layout)
    for r in routes.values():
        xy = _clean([layout.xy(m, c) for m, c in r.points])
        r.points = xy
        _shape(r)
    return routes


# ------------------------------------------------------------------------ sides
def _sides(tad: Tad, layout: Layout) -> dict[str, tuple[str, str]]:
    """Which side each end of each edge uses: far (+main), near, lo (-cross) or hi."""
    out = {}
    for e in tad.edges.values():
        a, b = layout.tier[e.src], layout.tier[e.dst]
        if b > a:
            out[e.id] = ("far", "near")
        elif b < a:
            out[e.id] = ("near", "far")
        elif _between(tad, layout, e.src, e.dst):
            out[e.id] = ("far", "far")
        else:
            below = _center(layout, e.dst)[1] > _center(layout, e.src)[1]
            out[e.id] = ("hi", "lo") if below else ("lo", "hi")
    return out


def _center(layout: Layout, nid: str) -> Pt:
    r = layout.nodes[nid]
    return layout.main(r.cx, r.cy)


def _between(tad: Tad, layout: Layout, a: str, b: str) -> bool:
    """Whether another node of the same tier sits between a and b."""
    ca, cb = _center(layout, a)[1], _center(layout, b)[1]
    lo, hi = min(ca, cb), max(ca, cb)
    tier = layout.tier[a]
    return any(
        layout.tier[n] == tier and lo < _center(layout, n)[1] < hi
        for n in tad.nodes
        if n not in (a, b)
    )


def _ports(
    tad: Tad, layout: Layout, sides: dict[str, tuple[str, str]]
) -> dict[tuple[str, int], Pt]:
    """Port point (main, cross) for each (edge id, end): 0 the source, 1 the target."""
    hm, hc = layout.half
    groups: dict[tuple[str, str], list[tuple[float, str, int]]] = {}
    for e in tad.edges.values():
        for end, (node, other) in enumerate(((e.src, e.dst), (e.dst, e.src))):
            side = sides[e.id][end]
            om, oc = _center(layout, other)
            key = oc if side in ("far", "near") else om
            groups.setdefault((node, side), []).append((key, e.id, end))
    ports: dict[tuple[str, int], Pt] = {}
    for (node, side), items in groups.items():
        items.sort()
        m, c = _center(layout, node)
        span = 2 * (hc if side in ("far", "near") else hm)
        gap = min(16.0, span * 0.8 / max(len(items), 1))
        for i, (_, eid, end) in enumerate(items):
            off = (i - (len(items) - 1) / 2) * gap
            if side == "far":
                ports[(eid, end)] = (m + hm, c + off)
            elif side == "near":
                ports[(eid, end)] = (m - hm, c + off)
            elif side == "hi":
                ports[(eid, end)] = (m + off, c + hc)
            else:
                ports[(eid, end)] = (m + off, c - hc)
    return ports


# ---------------------------------------------------------------------- routing
def _route(
    e: Edge, layout: Layout, sides: tuple[str, str], ports: dict[tuple[str, int], Pt]
) -> list[Pt]:
    p0, p3 = ports[(e.id, 0)], ports[(e.id, 1)]
    skip = {e.src, e.dst}
    a, b = layout.tier[e.src], layout.tier[e.dst]
    if sides[0] in ("hi", "lo"):
        return [p0, (p0[0], p3[1])]
    if sides == ("far", "far"):
        g = layout.gutters[a + 1]
        return [p0, (g, p0[1]), (g, p3[1]), p3]
    if abs(p0[1] - p3[1]) < 3 and _free(layout, p0[0], p3[0], p0[1], skip):
        return [p0, (p3[0], p0[1])]
    lo, hi = (a, b) if b > a else (b, a)
    first = a if b > a else a - 1
    last = b - 1 if b > a else b
    order = [first, last, *[k for k in range(lo, hi) if k not in (first, last)]]
    for k in order:
        g = layout.gutters[k + 1]
        if _free(layout, p0[0], g, p0[1], skip) and _free(layout, g, p3[0], p3[1], skip):
            return [p0, (g, p0[1]), (g, p3[1]), p3]
    g1 = layout.gutters[first + 1]
    g2 = layout.gutters[last + 1]
    lane = _channel(layout, g1, g2, (p0[1] + p3[1]) / 2, skip)
    return [p0, (g1, p0[1]), (g1, lane), (g2, lane), (g2, p3[1]), p3]


def _free(layout: Layout, m0: float, m1: float, c: float, skip: set[str]) -> bool:
    """Whether a run along main from m0 to m1 at cross c misses every other box."""
    lo, hi = min(m0, m1), max(m0, m1)
    for nid, rect in layout.nodes.items():
        if nid in skip:
            continue
        rm, rc = layout.main(rect.cx, rect.cy)
        hm, hc = layout.half
        if rm + hm + CLEAR > lo and rm - hm - CLEAR < hi and abs(rc - c) < hc + CLEAR:
            return False
    return True


def _channel(layout: Layout, m0: float, m1: float, goal: float, skip: set[str]) -> float:
    """The free cross position nearest `goal` for a run between two gutters."""
    hm, hc = layout.half
    edges: list[float] = []
    for nid, rect in layout.nodes.items():
        rm, rc = layout.main(rect.cx, rect.cy)
        if nid not in skip and min(m0, m1) < rm < max(m0, m1):
            edges += [rc - hc, rc + hc]
    if not edges:
        return goal
    edges.sort()
    candidates = [edges[0] - 3 * CLEAR, edges[-1] + 3 * CLEAR]
    candidates += [(x + y) / 2 for x, y in zip(edges[1::2], edges[2::2], strict=False)]
    candidates.sort(key=lambda c: abs(c - goal))
    for c in candidates:
        if _free(layout, m0, m1, c, skip):
            return c
    return candidates[0]


def _tracks(routes: dict[str, Route], layout: Layout) -> None:
    """Give lines that share a gutter their own tracks, so they run side by side."""
    runs: dict[int, list[tuple[float, float, Route, int]]] = {}
    for r in routes.values():
        for i in range(len(r.points) - 1):
            (m0, c0), (m1, c1) = r.points[i], r.points[i + 1]
            if abs(m0 - m1) > 0.01 or abs(c0 - c1) < 0.01:
                continue
            for g, gm in enumerate(layout.gutters):
                if abs(m0 - gm) < 0.01:
                    runs.setdefault(g, []).append((min(c0, c1), max(c0, c1), r, i))
    for items in runs.values():
        items.sort(key=lambda it: (it[0], it[1]))
        ends: list[float] = []
        chosen = []
        for lo, hi, r, i in items:
            for t, end in enumerate(ends):
                if end + TRACK < lo:
                    ends[t] = hi
                    break
            else:
                ends.append(hi)
                t = len(ends) - 1
            chosen.append((t, r, i))
        n = len(ends)
        for t, r, i in chosen:
            off = (t - (n - 1) / 2) * TRACK
            for j in (i, i + 1):
                m, c = r.points[j]
                r.points[j] = (m + off, c)


# ---------------------------------------------------------------------- drawing
def _clean(points: list[Pt]) -> list[Pt]:
    out: list[Pt] = []
    for p in points:
        if out and math.dist(out[-1], p) < 0.5:
            continue
        if len(out) >= 2 and _collinear(out[-2], out[-1], p):
            out[-1] = p
            continue
        out.append(p)
    return out


def _collinear(a: Pt, b: Pt, c: Pt) -> bool:
    return abs((b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])) < 0.5


def _unit(a: Pt, b: Pt) -> Pt:
    length = math.dist(a, b) or 1.0
    return ((b[0] - a[0]) / length, (b[1] - a[1]) / length)


def rounded(points: list[Pt], radius: float = RADIUS) -> tuple[str, float]:
    """Path data with round corners, and its length."""
    if len(points) < 2:
        return "", 0.0
    d = f"M{points[0][0]:.1f} {points[0][1]:.1f}"
    length = 0.0
    here = points[0]
    for i in range(1, len(points) - 1):
        a, p, b = points[i - 1], points[i], points[i + 1]
        u, v = _unit(a, p), _unit(p, b)
        turn = math.acos(max(-1.0, min(1.0, u[0] * v[0] + u[1] * v[1])))
        cut = min(radius, math.dist(a, p) / 2, math.dist(p, b) / 2)
        if turn < 1e-3 or cut < 0.5:
            length += math.dist(here, p)
            d += f" L{p[0]:.1f} {p[1]:.1f}"
            here = p
            continue
        r = cut / math.tan(turn / 2)
        start = (p[0] - u[0] * cut, p[1] - u[1] * cut)
        end = (p[0] + v[0] * cut, p[1] + v[1] * cut)
        sweep = 1 if u[0] * v[1] - u[1] * v[0] > 0 else 0
        length += math.dist(here, start) + r * turn
        d += f" L{start[0]:.1f} {start[1]:.1f}"
        d += f" A{r:.1f} {r:.1f} 0 0 {sweep} {end[0]:.1f} {end[1]:.1f}"
        here = end
    last = points[-1]
    length += math.dist(here, last)
    d += f" L{last[0]:.1f} {last[1]:.1f}"
    return d, length


def _shape(r: Route) -> None:
    pts = r.points
    r.full, r.length = rounded(pts)
    line = list(pts)
    heads = [(pts[-2], pts[-1])]
    if r.edge.both:
        heads.append((pts[1], pts[0]))
    for k, (a, b) in enumerate(heads):
        u = _unit(a, b)
        trim = min(HEAD - 2, math.dist(a, b) / 3)
        line[-1 if k == 0 else 0] = (b[0] - u[0] * trim, b[1] - u[1] * trim)
        r.heads.append(arrowhead(a, b, r.edge.style))
    r.line, r.line_length = rounded(line)
    if r.edge.label:
        r.label = _label_spot(pts, r.edge.label)


def arrowhead(a: Pt, b: Pt, style: str) -> str:
    """Path data for a head at b pointing away from a: filled for sync, open for async."""
    u = _unit(a, b)
    base = (b[0] - u[0] * HEAD, b[1] - u[1] * HEAD)
    n = (-u[1] * 4.6, u[0] * 4.6)
    p1 = f"{base[0] + n[0]:.1f} {base[1] + n[1]:.1f}"
    p2 = f"{base[0] - n[0]:.1f} {base[1] - n[1]:.1f}"
    tip = f"{b[0]:.1f} {b[1]:.1f}"
    return f"M{p1} L{tip} L{p2}" if style == "async" else f"M{tip} L{p1} L{p2}Z"


def _label_spot(pts: list[Pt], words: str) -> tuple[float, float, str]:
    """Middle of the longest level run that holds the words, else of the longest run.

    A label above a level run reads in line with it; beside an upright run it reads
    across the gutter, where other lines may pass.
    """
    runs = range(len(pts) - 1)
    need = len(words) * 12 * 0.55 + 16
    level = [i for i in runs if abs(pts[i][1] - pts[i + 1][1]) < 0.5]
    roomy = [i for i in level if math.dist(pts[i], pts[i + 1]) >= need]
    best = max(roomy or runs, key=lambda i: math.dist(pts[i], pts[i + 1]))
    (x0, y0), (x1, y1) = pts[best], pts[best + 1]
    if abs(y0 - y1) < 0.5:
        return ((x0 + x1) / 2, y0 - 7, "middle")
    return (x0 + 7, (y0 + y1) / 2 + 4, "start")


def bounds(rects: list[Rect], routes: list[Route]) -> Rect:
    """The box around every node, group and line."""
    xs = [r.x for r in rects] + [r.x + r.w for r in rects]
    ys = [r.y for r in rects] + [r.y + r.h for r in rects]
    for route in routes:
        xs += [p[0] for p in route.points]
        ys += [p[1] for p in route.points]
    return Rect(min(xs), min(ys), max(xs) - min(xs), max(ys) - min(ys))
