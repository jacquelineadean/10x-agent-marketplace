"""Where each TAD part goes: tiers along the direction of travel, lanes across it.

Tiers come from the edges (a node sits one tier after the furthest node that calls it)
unless the node names its own. Lanes come from packing: each group is a block of rows
that holds its nodes and nested groups. Inside a block, and at the top, nodes and inner
blocks are seated one by one, the most linked first, each in the free rows nearest the
parts it links to, so groups never overlap and talkers sit level. A group's box is its
contents plus padding, with room above for its label.

Coordinates are worked out on two axes, `main` (along tiers) and `cross` (along
lanes), then mapped to x and y for the direction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from chronicle.core.motion.tad.spec import Tad

NODE_W = 188.0
NODE_H = 64.0
NODE_H_TALL = 82.0
ROW = 22.0  # packing unit across tiers, in pixels
TIER_GAP = {"right": 100.0, "down": 84.0}
LANE_GAP = {"right": 44.0, "down": 36.0}
PAD = 20.0
LABEL = 24.0
# Rows a group adds before and after its contents: the label sits on the top side.
BORDER = {"right": (2, 1), "down": (1, 1)}


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    w: float
    h: float

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

    def hits(self, other: Rect, margin: float = 0.0) -> bool:
        return not (
            self.x + self.w + margin <= other.x
            or other.x + other.w + margin <= self.x
            or self.y + self.h + margin <= other.y
            or other.y + other.h + margin <= self.y
        )


@dataclass
class Layout:
    """Pixel boxes for nodes and groups, the tier of each node, and the gutters."""

    direction: str
    node_w: float
    node_h: float
    nodes: dict[str, Rect]
    groups: dict[str, Rect]
    tier: dict[str, int]
    # Main-axis center of the gutter before tier t, for t from 0 to last + 1.
    gutters: list[float]
    warnings: list[str] = field(default_factory=list)

    def main(self, x: float, y: float) -> tuple[float, float]:
        """(x, y) to (main, cross)."""
        return (x, y) if self.direction == "right" else (y, x)

    def xy(self, m: float, c: float) -> tuple[float, float]:
        """(main, cross) to (x, y)."""
        return (m, c) if self.direction == "right" else (c, m)

    @property
    def half(self) -> tuple[float, float]:
        """Half a node's extent along (main, cross)."""
        w, h = self.node_w / 2, self.node_h / 2
        return (w, h) if self.direction == "right" else (h, w)


def place(tad: Tad, tall: bool) -> Layout:
    """Lay the diagram out; `tall` gives every node room for a two-line label."""
    d = tad.direction
    node_h = NODE_H_TALL if tall else NODE_H
    node_main, node_cross = (NODE_W, node_h) if d == "right" else (node_h, NODE_W)
    k = math.ceil((node_cross + LANE_GAP[d]) / ROW)
    tiers = _tiers(tad)
    if all(n.lane is not None for n in tad.nodes.values()):
        rows = {n.id: float(n.lane or 0) * k for n in tad.nodes.values()}
    else:
        rows = _Packer(tad, tiers, k, BORDER[d]).rows()
    last = max(tiers.values(), default=0)
    centers = _tier_centers(tad, tiers, last, node_main)
    nodes = {}
    for nid, t in tiers.items():
        m = centers[t]
        c = (rows[nid] + k / 2) * ROW
        x, y = (m, c) if d == "right" else (c, m)
        nodes[nid] = Rect(x - NODE_W / 2, y - node_h / 2, NODE_W, node_h)
    gutters = [centers[0] - node_main / 2 - TIER_GAP[d] / 2]
    for t in range(last):
        gutters.append((centers[t] + centers[t + 1]) / 2)
    gutters.append(centers[last] + node_main / 2 + TIER_GAP[d] / 2)
    layout = Layout(d, NODE_W, node_h, nodes, {}, tiers, gutters)
    layout.groups = _group_boxes(tad, layout)
    layout.warnings.extend(_overlaps(tad, layout))
    return layout


# ------------------------------------------------------------------------ tiers
def _tiers(tad: Tad) -> dict[str, int]:
    """Longest path from the sources, ignoring edges that close a loop."""
    order = list(tad.nodes)
    out_edges: dict[str, list[str]] = {n: [] for n in order}
    for e in tad.edges.values():
        out_edges[e.src].append(e.dst)
    preds: dict[str, list[str]] = {n: [] for n in order}
    state: dict[str, int] = {}
    finished: list[str] = []
    for start in order:
        if start in state:
            continue
        stack = [(start, iter(out_edges[start]))]
        state[start] = 1
        while stack:
            node, it = stack[-1]
            nxt = next(it, None)
            if nxt is None:
                state[node] = 2
                finished.append(node)
                stack.pop()
            elif state.get(nxt) == 1:
                continue  # an edge back up the path closes a loop; it does not set tiers
            else:
                preds[nxt].append(node)
                if nxt not in state:
                    state[nxt] = 1
                    stack.append((nxt, iter(out_edges[nxt])))
    tier: dict[str, int] = {}
    for node in reversed(finished):
        given = tad.nodes[node].tier
        base = max((tier[p] + 1 for p in preds[node] if p in tier), default=0)
        tier[node] = given if given is not None else base
    return tier


def _tier_centers(tad: Tad, tiers: dict[str, int], last: int, node_main: float) -> list[float]:
    """Main-axis center of each tier; gaps widen where group boxes start or end."""
    d = tad.direction
    spans = {}
    for gid in tad.groups:
        members = [tiers[n] for n in tad.members(gid)]
        if members:
            spans[gid] = (min(members), max(members))
    start_pad = PAD + (LABEL if d == "down" else 0.0)
    centers = [node_main / 2]
    for t in range(last):
        extra = sum(PAD for lo, hi in spans.values() if hi == t)
        extra += sum(start_pad for lo, hi in spans.values() if lo == t + 1)
        centers.append(centers[-1] + node_main + TIER_GAP[d] + extra)
    return centers


# ------------------------------------------------------------------------ lanes
@dataclass
class _Block:
    lo: int
    hi: int
    height: int
    rows: dict[str, float] = field(default_factory=dict)


class _Packer:
    """Stack nodes and group blocks, each as near the parts it links to as it fits."""

    def __init__(self, tad: Tad, tiers: dict[str, int], k: int, border: tuple[int, int]) -> None:
        self.tad = tad
        self.tiers = tiers
        self.k = k
        self.border = border
        self.links: dict[str, list[str]] = {n: [] for n in tad.nodes}
        for e in tad.edges.values():
            self.links[e.src].append(e.dst)
            self.links[e.dst].append(e.src)

    def rows(self) -> dict[str, float]:
        block = self._block(None)
        low = min(block.rows.values(), default=0.0)
        return {n: r - low for n, r in block.rows.items()}

    def _block(self, gid: str | None) -> _Block:
        items = [self._block(c.id) for c in self.tad.groups.values() if c.parent == gid]
        items = [b for b in items if b.rows]
        members = [n.id for n in self.tad.nodes.values() if n.group == gid]
        for nid in members:
            t = self.tiers[nid]
            items.append(_Block(t, t, self.k, {nid: 0.0}))
        taken: list[tuple[int, int, float, float]] = []
        rows: dict[str, float] = {}
        while items:
            item = max(items, key=lambda b: (self._pull(b, rows), -items.index(b)))
            items.remove(item)
            at = self._spot(item, taken, rows)
            taken.append((item.lo, item.hi, at, at + item.height))
            rows.update({n: r + at for n, r in item.rows.items()})
        if not rows:
            return _Block(0, 0, 0)
        self._settle(members, taken, rows)
        # Inner blocks reach past their nodes by their own borders, so measure the items.
        top = min(a for _, _, a, _ in taken)
        bottom = max(b for *_, b in taken)
        if gid is None:
            height = int(bottom - top)
        else:
            rows = {n: r - top + self.border[0] for n, r in rows.items()}
            height = int(bottom - top) + self.border[0] + self.border[1]
        spread = [self.tiers[n] for n in rows]
        return _Block(min(spread), max(spread), height, rows)

    def _pull(self, item: _Block, rows: dict[str, float]) -> int:
        """How many links run from the item to parts already placed."""
        return sum(m in rows for n in item.rows for m in self.links[n])

    def _spot(
        self, item: _Block, taken: list[tuple[int, int, float, float]], rows: dict[str, float]
    ) -> float:
        """The free row nearest where the item's links pull it, else the first free row."""
        wants = [rows[m] - item.rows[n] for n in item.rows for m in self.links[n] if m in rows]
        if not wants:
            return _first_fit(taken, item.lo, item.hi, item.height)
        goal = round(sum(wants) / len(wants))
        for step in range(800):
            at = goal + (step + 1) // 2 * (1 if step % 2 else -1)
            if not _clash(taken, item.lo, item.hi, at, at + item.height):
                return float(at)
        return _first_fit(taken, item.lo, item.hi, item.height)

    def _settle(
        self, members: list[str], taken: list[tuple[int, int, float, float]], rows: dict[str, float]
    ) -> None:
        """Move each lone node to the free rows nearest the middle of its neighbors.

        Seating runs in one pass, so a node placed early sits level with only the first
        part it links to; once all are in, it moves between them, as a fan-out reads.
        """
        for _ in range(2):
            for nid in members:
                near = [rows[m] for m in self.links[nid] if m in rows]
                if not near:
                    continue
                t = self.tiers[nid]
                mine = (t, t, rows[nid], rows[nid] + self.k)
                others = [x for x in taken if x != mine]
                goal = round(sum(near) / len(near))
                for step in range(400):
                    at = goal + (step + 1) // 2 * (1 if step % 2 else -1)
                    if not _clash(others, t, t, at, at + self.k):
                        break
                taken[taken.index(mine)] = (t, t, float(at), float(at) + self.k)
                rows[nid] = float(at)


def _clash(
    taken: list[tuple[int, int, float, float]], lo: int, hi: int, a: float, b: float
) -> bool:
    return any(t0 <= hi and lo <= t1 and a < r1 and r0 < b for t0, t1, r0, r1 in taken)


def _first_fit(taken: list[tuple[int, int, float, float]], lo: int, hi: int, height: int) -> float:
    for at in sorted({0.0, *(b for *_, b in taken)}):
        if not _clash(taken, lo, hi, at, at + height):
            return at
    return 0.0


# ----------------------------------------------------------------------- groups
def _group_boxes(tad: Tad, layout: Layout) -> dict[str, Rect]:
    """Each group's box: its nodes and inner boxes, padded, with a label band on top."""
    boxes: dict[str, Rect] = {}

    def depth(gid: str) -> int:
        return len(tad.chain(gid))

    for gid in sorted(tad.groups, key=depth, reverse=True):
        parts = [layout.nodes[n] for n in tad.members(gid)]
        parts += [boxes[c] for c, g in tad.groups.items() if g.parent == gid and c in boxes]
        if not parts:
            continue
        x0 = min(p.x for p in parts) - PAD
        y0 = min(p.y for p in parts) - PAD - LABEL
        x1 = max(p.x + p.w for p in parts) + PAD
        y1 = max(p.y + p.h for p in parts) + PAD
        boxes[gid] = Rect(x0, y0, x1 - x0, y1 - y0)
    return boxes


def _overlaps(tad: Tad, layout: Layout) -> list[str]:
    out = []
    for gid, box in layout.groups.items():
        inside = set(tad.members(gid))
        for nid, rect in layout.nodes.items():
            if nid not in inside and box.hits(rect, -2):
                out.append(
                    f"node {nid} sits inside group {gid}'s box; give it a lane outside the group"
                )
        for other, obox in layout.groups.items():
            nested = gid in tad.chain(other) or other in tad.chain(gid)
            if other > gid and not nested and box.hits(obox, -2):
                out.append(f"groups {gid} and {other} overlap; move one of them to other lanes")
    return out
