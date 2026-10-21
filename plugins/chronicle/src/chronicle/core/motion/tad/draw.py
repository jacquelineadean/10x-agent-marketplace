"""Draw a TAD and give it motion: zones, components, lines, packets and state marks.

Each part is a stack of nested groups so every effect has its own track: the outer group
shows and hides, the next dims for focus, the next pulses, the innermost pops in, and
overlays turn on for states. A line draws itself on through a mask stroked from source
to target. A packet is a dot that runs along its line's path by its dash offset.
"""

from __future__ import annotations

import difflib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from chronicle.core.motion import stage
from chronicle.core.motion.model import Plan, Step
from chronicle.core.motion.parts import Life, named, packet
from chronicle.core.motion.tad import icons
from chronicle.core.motion.tad.layout import NODE_W, Rect, place
from chronicle.core.motion.tad.route import Route, arrowhead, bounds, route_all
from chronicle.core.motion.tad.spec import EDGE_STATES, NODE_STATES, Edge, Node, Tad
from chronicle.core.motion.timeline import Point, Timeline, changes, held, redraws, swells
from chronicle.core.story.html import tag
from chronicle.core.story.markup import plain
from chronicle.core.story.model import Report

LABEL_SIZE = 14.0
TECH_SIZE = 11.0
EDGE_LABEL_SIZE = 12.0
TEXT_X = 54.0  # text starts here inside a node, right of the icon tile
TEXT_W = NODE_W - TEXT_X - 12
DIM = {"node": 0.22, "edge": 0.15, "group": 0.4}
NODE_LAG = 0.12  # the first node a step shows appears this long after the step starts
STAGGER = 0.1  # and each next one this much later
EDGE_LAG = 0.35  # a line starts drawing once both its ends are in
STATE_LAG = 0.2
FLOW_LAG = 0.35  # a packet leaves this long into its step, later if the step shows parts
HOP_MIN, HOP_MAX = 0.45, 1.3
MARGIN = 18.0
TRAIL = 28.0
BADGES = {"new": "NEW", "legacy": "LEGACY", "down": "DOWN", "planned": "PLANNED"}
# Marks drawn in a 18 x 18 badge circle for states that read as a sign.
SIGNS = {
    "good": "M5.2 9.4l2.6 2.6 5-5.4",
    "warn": "M9 4.8v5.2 M9 13.2h.01",
    "bad": "M6 6l6 6 M12 6l-6 6",
}


@dataclass
class _Packet:
    edge: Edge
    forward: bool
    start: float
    end: float
    tone: str


# ------------------------------------------------------------------------ check
def check_steps(steps: Any, tad: Tad, report: Report) -> None:
    """Every id a step names must be a part of the TAD that the action applies to."""
    ids = sorted(tad.ids())
    for i, step in enumerate(steps if isinstance(steps, list) else []):
        if not isinstance(step, Mapping):
            continue
        where = f"steps[{i}]"
        for key in ("show", "hide", "focus", "draw", "pulse", "flow"):
            value = step.get(key, [])
            for x in value if isinstance(value, list) else []:
                if key == "flow" and x not in tad.flows and x not in tad.edges:
                    report.errors.append(f"{where}.flow names {x!r}; name a tad flow or an edge")
                elif x not in tad.ids():
                    report.errors.append(
                        f"{where}.{key} names {x!r}, which is not a part{_near(x, ids)}"
                    )
        states = step.get("state", {})
        for x, value in states.items() if isinstance(states, Mapping) else []:
            allowed = NODE_STATES if x in tad.nodes else EDGE_STATES
            if x not in tad.nodes and x not in tad.edges and x not in tad.groups:
                report.errors.append(
                    f"{where}.state names {x!r}; states apply to nodes, edges and groups"
                )
            elif value not in allowed:
                report.errors.append(f"{where}.state.{x} must be one of {', '.join(allowed)}")


def _near(x: str, ids: list[str]) -> str:
    match = difflib.get_close_matches(x, ids, n=1)
    return f" (did you mean {match[0]}?)" if match else ""


def default_steps(tad: Tad) -> list[dict[str, Any]]:
    """Steps for a TAD that gives none: tiers come in one by one, then each flow runs."""
    tiers: dict[int, list[str]] = {}
    for nid, t in place(tad, False).tier.items():
        tiers.setdefault(t, []).append(nid)
    steps: list[dict[str, Any]] = [
        {"show": nodes} for _, nodes in sorted(tiers.items()) if len(tiers) > 1
    ]
    steps += [{"caption": f.label, "flow": [f.id]} for f in tad.flows.values()]
    return steps


def floor(raw: Mapping[str, Any], tad: Tad) -> float:
    """The least time a step needs for its packets to travel at a readable speed."""
    hops = 0
    for x in raw.get("flow", []):
        hops = max(hops, len(tad.flows[x].hops) if x in tad.flows else 1)
    if not hops:
        return 0.0
    return _flow_lag(raw) + hops * 0.75 + 0.6


def _flow_lag(step: Mapping[str, Any] | Step) -> float:
    if isinstance(step, Step):
        shows = bool(step.show or step.draw)
    else:
        shows = bool(step.get("show") or step.get("draw"))
    return FLOW_LAG + (0.6 if shows else 0.0)


def captions(plan: Plan, tad: Tad) -> None:
    """A step without a caption that runs a labelled flow takes the flow's label."""
    for step in plan.steps:
        if not step.caption:
            labels = [tad.flows[x].label for x in step.flow if x in tad.flows]
            step.caption = next((x for x in labels if x), "")


# ---------------------------------------------------------------------- drawing
def figure(tad: Tad, plan: Plan, box: stage.Box, timeline: Timeline) -> tuple[str, list[str]]:
    """The TAD's markup fitted into the stage box; its tracks go on the timeline."""
    drawing = _Drawing(tad, plan, timeline)
    return drawing.markup(box), drawing.warnings


class _Drawing:
    def __init__(self, tad: Tad, plan: Plan, timeline: Timeline) -> None:
        self.tad = tad
        self.plan = plan
        self.timeline = timeline
        self.slug = plan.slug
        self.warnings: list[str] = []
        self.text = {n.id: self._words(n) for n in tad.nodes.values()}
        tall = any(len(a) > 1 and b for a, b in self.text.values())
        self.layout = place(tad, tall)
        self.warnings += self.layout.warnings
        self.routes = route_all(tad, self.layout)
        self.life = self._lives()
        self.states: dict[str, list[tuple[float, str]]] = {}
        for step in plan.steps:
            for x, state in step.state.items():
                self.states.setdefault(x, []).append((step.start + STATE_LAG, state))
        self.pings: dict[str, list[float]] = {}
        self.hot: dict[str, list[tuple[float, float, float]]] = {}
        self.pulses: dict[str, list[float]] = {}
        self.packets = self._packets()
        for step in plan.steps:
            at = step.start + 0.25 + (0.5 if step.show or step.draw else 0.0)
            for x in _expand(tad, step.pulse):
                self.pulses.setdefault(x, []).append(at)
        self.defs: list[str] = []

    # ------------------------------------------------------------- words
    def _words(self, node: Node) -> tuple[list[str], list[str]]:
        lines = stage.wrap(node.label, TEXT_W, LABEL_SIZE, "sans")
        if len(lines) > 2:
            self.warnings.append(f"node {node.id}: label runs past two lines; shorten it")
            lines = [lines[0], lines[1] + "…"]
        tech = stage.wrap(node.tech, TEXT_W, TECH_SIZE, "mono") if node.tech else []
        if len(tech) > 1:
            self.warnings.append(f"node {node.id}: tech is cut to one line; shorten it")
            tech = [tech[0] + "…"]
        return lines, tech

    # -------------------------------------------------------------- when
    def _lives(self) -> dict[str, Life]:
        """When each part is on screen, from show and hide, then lines and zones by rule.

        A line nobody names comes in once both its ends are in; a zone nobody names is up
        while any part inside it is.
        """
        tad = self.tad
        events: dict[str, list[tuple[float, bool]]] = {}
        for step in self.plan.steps:
            shown = _expand(tad, [*step.show, *step.draw])
            nodes = [x for x in shown if x in tad.nodes]
            after = step.start + NODE_LAG + max(0, min(len(nodes), 9) - 1) * STAGGER + EDGE_LAG
            lines = 0
            for x in shown:
                if x in tad.groups:
                    t = step.start
                elif x in tad.nodes:
                    t = step.start + NODE_LAG + min(nodes.index(x), 8) * STAGGER
                else:
                    t = after + min(lines, 8) * 0.08
                    lines += 1
                events.setdefault(x, []).append((t, True))
            for x in _expand(tad, step.hide):
                events.setdefault(x, []).append((step.start, False))
        life = named(events)
        for nid in tad.nodes:
            life.setdefault(nid, Life())
        for eid, edge in tad.edges.items():
            if eid not in life:
                life[eid] = _joined([life[edge.src], life[edge.dst]], all, EDGE_LAG)
        for gid in sorted(tad.groups, key=lambda g: -len(tad.chain(g))):
            if gid not in life:
                parts = [life[n.id] for n in tad.nodes.values() if n.group == gid]
                parts += [life[c] for c, g in tad.groups.items() if g.parent == gid and c in life]
                life[gid] = _joined(parts, any, -0.1)
        return life

    def _packets(self) -> list[_Packet]:
        out = []
        for step in self.plan.steps:
            start = step.start + _flow_lag(step)
            for x in step.flow:
                flow = self.tad.flows.get(x)
                hops = flow.hops if flow else [(self.tad.edges[x], True)]
                tone = flow.tone if flow else "accent"
                each = (step.end - 0.45 - start) / len(hops)
                each = min(HOP_MAX, max(HOP_MIN, each))
                for k, (edge, forward) in enumerate(hops):
                    t0 = start + k * each
                    t1 = t0 + each * 0.92
                    out.append(_Packet(edge, forward, t0, t1, tone))
                    target = edge.dst if forward else edge.src
                    self.pings.setdefault(target, []).append(t1)
                    self.hot.setdefault(edge.id, []).append((t0, t1 + 0.25, 0.3))
        return out

    # ------------------------------------------------------------ markup
    def markup(self, box: stage.Box) -> str:
        lay = self.layout
        rects = list(lay.nodes.values()) + list(lay.groups.values())
        labels = [self._label_box(r) for r in self.routes.values() if r.label]
        area = bounds(rects + [x for x in labels if x], list(self.routes.values()))
        legend, legend_box = self._legend(area.x, area.y + area.h + 30)
        if legend_box:
            area = bounds([area, legend_box], [])
        area = Rect(area.x - MARGIN, area.y - MARGIN, area.w + 2 * MARGIN, area.h + 2 * MARGIN)
        scale, ox, oy = stage.fit(area.w, area.h, box, most=1.3 * self.plan.unit)
        if scale < 0.62:
            self.warnings.append(
                f"the TAD is shrunk to {scale:.0%} to fit the frame, so its text is small; "
                "use a wider frame (wide or 16:9), direction down for tall frames, or fewer parts"
            )
        self.area = area
        groups = sorted(self.tad.groups, key=lambda g: len(self.tad.chain(g)))
        body = "".join(self._group(g) for g in groups if g in lay.groups)
        body += "".join(self._edge(e) for e in self.tad.edges.values())
        body += "".join(self._packet(i, p) for i, p in enumerate(self.packets))
        body += "".join(self._node(n) for n in self.tad.nodes.values())
        body += legend
        defs = tag("defs", "".join(self.defs)) if self.defs else ""
        move = f"translate({ox - area.x * scale:.2f} {oy - area.y * scale:.2f}) scale({scale:.4f})"
        return tag("g", defs + body, class_="m-tad", transform=move)

    # ------------------------------------------------------------ groups
    def _group(self, gid: str) -> str:
        g = self.tad.groups[gid]
        r = self.layout.groups[gid]
        base = f"{self.slug}-g-{gid}"
        style = f"m-{g.style}"
        shape = {
            "x": f"{r.x:.1f}",
            "y": f"{r.y:.1f}",
            "width": f"{r.w:.1f}",
            "height": f"{r.h:.1f}",
        }
        inner = tag("rect", class_=f"m-gfill {style}", rx=14, **shape)
        inner += tag("rect", class_=f"m-gline {style}", id=f"{base}-o", rx=14, **shape)
        inner += tag(
            "text",
            plain(g.label.upper()),
            class_="m-glabel",
            x=f"{r.x + 14:.1f}",
            y=f"{r.y + 19:.1f}",
        )
        if gid in self.pulses:
            inner += tag("rect", class_="m-gflash", id=f"{base}-h", rx=14, **shape)
            self._flash(f"#{base}-h", [w for t in self.pulses[gid] for w in _twice(t, 0.9)])
        inner += self._overlays(
            gid, base, lambda s: tag("rect", class_=f"m-ring m-{s}", rx=14, **shape)
        )
        tone = g.tone or ("accent" if g.style == "cluster" else "")
        css = "m-group m-tinted" if tone else "m-group"
        dim = tag("g", inner, id=f"{base}-d")
        self._dim(gid, f"#{base}-d", "group")
        self._visible(gid, f"#{base}")
        return tag("g", dim, id=base, class_=css, style=f"--tone: var(--{tone})" if tone else None)

    # ------------------------------------------------------------- edges
    def _edge(self, edge: Edge) -> str:
        route = self.routes[edge.id]
        base = f"{self.slug}-e-{edge.id}"
        tone = next((p.tone for p in self.packets if p.edge.id == edge.id), None)
        hue = f"--tone: var(--{tone})" if tone else None
        lines = tag("path", class_="m-hot", id=f"{base}-h", d=route.line, style=hue)
        lines += tag("g", self._line(route, ""), id=f"{base}-b")
        lines += self._overlays(edge.id, base, lambda s: self._line(route, f" m-{s}"))
        if edge.id in self.hot or edge.id in self.pulses:
            spans = list(self.hot.get(edge.id, []))
            spans += [w for t in self.pulses.get(edge.id, []) for w in _twice(t, 0.55)]
            self._flash(f"#{base}-h", spans)
        life = self.life[edge.id]
        mask = None
        shows = [t for t, v in life.events if v]
        if shows:
            mask = f"{self.slug}-mk-{edge.id}"
            self._mask(mask, route, shows, life.initial)
        inner = tag("g", lines, mask=f"url(#{mask})" if mask else None)
        if route.label:
            x, y, anchor = route.label
            inner += tag(
                "text",
                plain(edge.label),
                class_="m-elabel",
                id=f"{base}-l",
                x=f"{x:.1f}",
                y=f"{y:.1f}",
                text_anchor=anchor,
            )
            if shows:
                self._label_after(f"#{base}-l", route, shows, life.initial)
        dim = tag("g", inner, id=f"{base}-d")
        self._dim(edge.id, f"#{base}-d", "edge")
        self._visible(edge.id, f"#{base}")
        return tag("g", dim, id=base, class_=f"m-edge m-{edge.style}")

    def _line(self, route: Route, extra: str) -> str:
        heads = "".join(tag("path", class_="m-head" + extra, d=h) for h in route.heads)
        return tag("path", class_="m-line" + extra, d=route.line) + heads

    def _mask(self, mid: str, route: Route, shows: list[float], visible: bool) -> None:
        """A stroke along the line that grows from source to target at each show."""
        a = self.area
        length = max(route.length, 1.0)
        span = _draw_time(route)
        path = tag(
            "path",
            class_="m-mask",
            id=f"{mid}-p",
            d=route.full,
            pathLength=f"{length:.1f}",
            stroke_dasharray=f"{length:.1f} {length:.1f}",
        )
        self.defs.append(
            tag(
                "mask",
                path,
                id=mid,
                maskUnits="userSpaceOnUse",
                x=f"{a.x:.0f}",
                y=f"{a.y:.0f}",
                width=f"{a.w:.0f}",
                height=f"{a.h:.0f}",
            )
        )
        points = redraws(length, shows, span, visible)
        self.timeline.add(f"#{mid}-p", "stroke-dashoffset", points, rest=0.0)

    def _label_after(self, selector: str, route: Route, shows: list[float], drawn: bool) -> None:
        """The edge's label fades in as its line finishes drawing, never ahead of it."""
        span = _draw_time(route)
        points: list[Point] = [(0.0, 1.0 if drawn else 0.0)]
        for t in shows:
            points += [(max(0.0, t - 0.02), points[-1][1]), (t, 0.0)]
            points += [(t + span * 0.7, 0.0), (t + span + 0.15, 1.0)]
        self.timeline.add(selector, "opacity", held(points), rest=1.0)

    def _label_box(self, route: Route) -> Rect | None:
        if not route.label:
            return None
        x, y, anchor = route.label
        w = len(route.edge.label) * EDGE_LABEL_SIZE * stage.GLYPH["sans"]
        left = x - w / 2 if anchor == "middle" else x
        return Rect(left, y - EDGE_LABEL_SIZE, w, EDGE_LABEL_SIZE + 4)

    # ----------------------------------------------------------- packets
    def _packet(self, index: int, p: _Packet) -> str:
        route = self.routes[p.edge.id]
        return packet(
            f"{self.slug}-pk-{index}",
            route.full,
            max(route.length, 1.0),
            TRAIL,
            (p.start, p.end),
            p.forward,
            self.timeline,
            style=f"--tone: var(--{p.tone})",
        )

    # ------------------------------------------------------------- nodes
    def _node(self, node: Node) -> str:
        r = self.layout.nodes[node.id]
        base = f"{self.slug}-n-{node.id}"
        tone = node.tone or icons.TONES.get(node.kind, "s1")
        shape = {
            "x": f"{r.x:.1f}",
            "y": f"{r.y:.1f}",
            "width": f"{r.w:.1f}",
            "height": f"{r.h:.1f}",
        }
        content = ""
        for k in range(min(node.replicas, 3) - 1, 0, -1):
            content += tag(
                "rect",
                class_="m-rep",
                rx=10,
                **{**shape, "x": f"{r.x + 4 * k:.1f}", "y": f"{r.y + 4 * k:.1f}"},
            )
        content += tag("rect", class_="m-shadow", rx=10, **{**shape, "y": f"{r.y + 2:.1f}"})
        content += tag("rect", class_="m-box", rx=10, **shape)
        content += tag("rect", class_="m-outline", id=f"{base}-o", rx=10, **shape)
        content += self._icon(node.kind, r.x + 12, r.cy - 16)
        content += self._node_text(node, r)
        if node.replicas > 1:
            content += _pill(f"×{node.replicas}", r.x + r.w - 6, r.y + r.h, "m-count")
        ping = ""
        if node.id in self.pings:
            ping = tag("rect", class_="m-ping", id=f"{base}-g", rx=10, **shape)
            self._ping(f"#{base}-g", self.pings[node.id])
        overlays = self._overlays(node.id, base, lambda s: self._mark(s, r, shape))
        fades = [
            (t, 0.45 if s in ("down", "planned") else 1.0) for t, s in self.states.get(node.id, [])
        ]
        if any(v < 1 for _, v in fades):
            self.timeline.add(f"#{base}-c", "opacity", changes(1.0, fades), rest=fades[-1][1])
        pop = tag("g", ping + tag("g", content, id=f"{base}-c") + overlays, id=f"{base}-p")
        self._pop(node.id, f"#{base}-p")
        pulse = tag("g", pop, id=f"{base}-u")
        if node.id in self.pulses:
            self._pulse(f"#{base}-u", self.pulses[node.id])
        dim = tag("g", pulse, id=f"{base}-d")
        self._dim(node.id, f"#{base}-d", "node")
        self._visible(node.id, f"#{base}")
        return tag("g", dim, id=base, class_="m-node", style=f"--tone: var(--{tone})")

    def _icon(self, kind: str, x: float, y: float) -> str:
        tile = tag("rect", class_="m-tile", x=f"{x:.1f}", y=f"{y:.1f}", width=32, height=32, rx=8)
        move = f"translate({x + 6.4:.1f} {y + 6.4:.1f}) scale(0.8)"
        return tile + tag("path", class_="m-glyph", d=icons.GLYPHS[kind], transform=move)

    def _node_text(self, node: Node, r: Rect) -> str:
        lines, tech = self.text[node.id]
        block = 17 * len(lines) + (15 if tech else 0)
        top = r.cy - block / 2
        x = r.x + TEXT_X
        out = ""
        for i, line in enumerate(lines):
            out += tag(
                "text", plain(line), class_="m-nlabel", x=f"{x:.1f}", y=f"{top + 13 + 17 * i:.1f}"
            )
        if tech:
            y = top + 17 * len(lines) + 12
            out += tag("text", plain(tech[0]), class_="m-tech", x=f"{x:.1f}", y=f"{y:.1f}")
        return out

    def _mark(self, state: str, r: Rect, shape: Mapping[str, str]) -> str:
        """The ring and badge a node wears in one state."""
        ring = tag("rect", class_=f"m-ring m-{state}", rx=10, **shape)
        if state in SIGNS:
            cx, cy = r.x + r.w - 4, r.y + 2
            badge = tag("circle", class_=f"m-badge m-{state}", cx=f"{cx:.1f}", cy=f"{cy:.1f}", r=9)
            move = f"translate({cx - 9:.1f} {cy - 9:.1f})"
            return ring + badge + tag("path", class_="m-sign", d=SIGNS[state], transform=move)
        if state in BADGES:
            return ring + _pill(BADGES[state], r.x + r.w - 6, r.y, f"m-flag m-{state}")
        return ring

    def _legend(self, x: float, y: float) -> tuple[str, Rect | None]:
        if not self.tad.legend:
            return "", None
        out = ""
        left = x
        for style, words in self.tad.legend.items():
            line = f"M{left:.1f} {y:.1f} H{left + 26:.1f}"
            head = arrowhead((left, y), (left + 30, y), style)
            sample = tag("path", class_="m-line", d=line) + tag("path", class_="m-head", d=head)
            out += tag("g", sample, class_=f"m-edge m-{style}")
            out += tag(
                "text", plain(words), class_="m-legend", x=f"{left + 38:.1f}", y=f"{y + 4:.1f}"
            )
            left += 38 + len(words) * EDGE_LABEL_SIZE * stage.GLYPH["sans"] + 28
        return tag("g", out, class_="m-key"), Rect(x, y - 8, left - x, 16)

    # ------------------------------------------------------------ tracks
    def _visible(self, x: str, selector: str) -> None:
        life = self.life[x]
        if life.moves:
            self.timeline.add(selector, "opacity", life.points(), rest=life.final)

    def _dim(self, x: str, selector: str, kind: str) -> None:
        moves = []
        for step in self.plan.steps:
            bright = not step.focus or x in _focused(self.tad, step.focus)
            moves.append((step.start, 1.0 if bright else DIM[kind]))
        if any(v < 1 for _, v in moves):
            self.timeline.add(selector, "opacity", changes(1.0, moves), rest=1.0)

    def _pop(self, x: str, selector: str) -> None:
        shows = [t for t, v in self.life[x].events if v]
        if not shows:
            return
        grow: list[Point] = [(0.0, 1.0)]
        rise: list[Point] = [(0.0, (0.0, 0.0))]
        for t in shows:
            grow += [(max(0.0, t - 0.02), 1.0), (t, 0.94), (t + 0.45, 1.0)]
            rise += [(max(0.0, t - 0.02), (0.0, 0.0)), (t, (0.0, 6.0)), (t + 0.45, (0.0, 0.0))]
        self.timeline.add(selector, "scale", grow, rest=1.0, origin="center")
        self.timeline.add(selector, "translate", rise, rest=(0.0, 0.0))

    def _pulse(self, selector: str, starts: list[float]) -> None:
        self.timeline.add(selector, "scale", swells(starts), rest=1.0, origin="center")

    def _ping(self, selector: str, arrivals: list[float]) -> None:
        grow: list[Point] = [(0.0, 1.0)]
        for t in sorted(arrivals):
            grow += [(t, 1.0), (t + 0.6, 1.14), (t + 0.62, 1.0)]
        fade = _envelope([(t, t + 0.6, 0.8) for t in arrivals], 0.02, tail=True)
        self.timeline.add(selector, "scale", grow, rest=1.0, origin="center")
        self.timeline.add(selector, "opacity", fade, rest=0.0)

    def _flash(self, selector: str, spans: list[tuple[float, float, float]]) -> None:
        self.timeline.add(selector, "opacity", _envelope(spans, 0.15), rest=0.0)

    def _overlays(self, x: str, base: str, draw: Callable[[str], str]) -> str:
        """One overlay per state the part takes; the plain outline hides while any is on."""
        events = self.states.get(x, [])
        used = [s for s in dict.fromkeys(s for _, s in events) if s != "normal"]
        if not used:
            return ""
        out = ""
        for state in used:
            sid = f"{base}-s-{state}"
            moves = [(t, 1.0 if s == state else 0.0) for t, s in events]
            out += tag("g", draw(state), id=sid)
            self.timeline.add(f"#{sid}", "opacity", changes(0.0, moves), rest=moves[-1][1])
        plain_line = [(t, 1.0 if s == "normal" else 0.0) for t, s in events]
        outline = f"#{base}-b" if x in self.tad.edges else f"#{base}-o"
        self.timeline.add(outline, "opacity", changes(1.0, plain_line), rest=plain_line[-1][1])
        return out


# ---------------------------------------------------------------------- helpers
def _expand(tad: Tad, ids: Iterable[str]) -> list[str]:
    """Ids in order, with a flow standing for its parts and a group for what it holds."""
    out: dict[str, None] = {}
    for x in ids:
        if x in tad.flows:
            flow = tad.flows[x]
            out.update(dict.fromkeys(flow.nodes))
            out.update(dict.fromkeys(e.id for e, _ in flow.hops))
        elif x in tad.groups:
            out[x] = None
            out.update(dict.fromkeys(g for g in tad.groups if x in tad.chain(g)))
            out.update(dict.fromkeys(tad.members(x)))
        else:
            out[x] = None
    return list(out)


def _focused(tad: Tad, ids: Iterable[str]) -> set[str]:
    """What stays bright: the parts named, lines between them, and zones around them."""
    keep = set(_expand(tad, ids))
    for x in list(keep):
        if x in tad.edges:
            keep.update((tad.edges[x].src, tad.edges[x].dst))
    keep.update(e.id for e in tad.edges.values() if e.src in keep and e.dst in keep)
    for x in list(keep):
        group = (
            tad.nodes[x].group
            if x in tad.nodes
            else tad.groups[x].parent
            if x in tad.groups
            else None
        )
        keep.update(tad.chain(group))
    return keep


def _joined(parts: list[Life], rule: Callable[[Iterable[bool]], bool], lag: float) -> Life:
    """A part that is up when `rule` holds over other parts; it comes in `lag` after them."""
    times = sorted({t for p in parts for t, _ in p.events})
    current = rule(p.initial for p in parts)
    life = Life(current)
    for t in times:
        value = rule(p.at(t) for p in parts)
        if value != current:
            life.events.append((max(0.0, t + (lag if value else 0.0)), value))
            current = value
    return life


def _draw_time(route: Route) -> float:
    """Seconds a line takes to draw on: longer lines take longer, within limits."""
    return min(1.1, max(0.45, route.length / 520))


def _twice(t: float, span: float) -> list[tuple[float, float, float]]:
    return [(t, t + span / 2, 0.55), (t + span / 2 + 0.1, t + span + 0.1, 0.55)]


def _envelope(
    spans: list[tuple[float, float, float]], ramp: float, tail: bool = False
) -> list[Point]:
    """Opacity that rises to each span's peak at its start and is 0 by its end.

    With `tail` it fades out across the whole span, as a ping ring does.
    """

    def value(t: float) -> float:
        best = 0.0
        for a, b, peak in spans:
            if tail:
                v = peak * (1 - (t - a) / max(b - a, 1e-6)) if a <= t <= b else 0.0
            elif a - ramp <= t < a:
                v = peak * (t - a + ramp) / ramp
            elif a <= t <= b - ramp:
                v = peak
            elif b - ramp < t <= b:
                v = peak * (b - t) / ramp
            else:
                v = 0.0
            best = max(best, v)
        return best

    marks = {0.0}
    for a, b, _ in spans:
        marks.update((max(0.0, a - ramp), a, max(a, b - ramp), b, a - 0.001))
    return [(t, value(t)) for t in sorted(m for m in marks if m >= 0)]


def _pill(words: str, right: float, cy: float, css: str) -> str:
    w = len(words) * 6.2 + 12
    box = tag("rect", x=f"{right - w:.1f}", y=f"{cy - 8:.1f}", width=f"{w:.1f}", height=16, rx=8)
    text = tag(
        "text", plain(words), x=f"{right - w / 2:.1f}", y=f"{cy + 3.4:.1f}", text_anchor="middle"
    )
    return tag("g", box + text, class_=f"m-pill {css}")
