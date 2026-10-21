"""A technical architecture diagram (TAD) as data: components, zones, links and flows.

Claude writes what the system is made of; code places it, routes every line, and
plays it. The `tad` object of an animation:

    direction  right (tiers left to right, the default) or down (tiers top to bottom)
    groups     [{id, label, style: zone|boundary|cluster|external, parent, tone}]
    nodes      [{id, label, kind, tech, group, tier, lane, replicas, tone}]
    edges      [{id, from, to, label, style: sync|async, both}]
    flows      [{id, label, path: [node ids in order], tone}]
    legend     true (default when both edge styles appear), false, or {sync, async}

`tier` is the column along the direction of travel and `lane` the row across it. Leave
both out and code places every node from the edges; give `lane` to every node or none.
"""

from __future__ import annotations

import difflib
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.motion.tad.icons import GLYPHS
from chronicle.core.story.model import Report, check_text

DIRECTIONS = ("right", "down")
GROUP_STYLES = ("zone", "boundary", "cluster", "external")
EDGE_STYLES = ("sync", "async")
NODE_STATES = ("normal", "new", "legacy", "good", "warn", "bad", "down", "planned")
EDGE_STATES = ("normal", "new", "legacy", "bad", "down", "planned")
# Theme colors a group, node or flow may take.
TONES = ("accent", "legacy", "good", "warn", "bad", "muted", "ink", "s1", "s2", "s3", "s4", "s5")
_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]{0,40}$")
_TONE = re.compile(r"^c-[a-z][a-z0-9-]{0,24}$")


@dataclass
class Group:
    id: str
    label: str
    style: str = "zone"
    parent: str | None = None
    tone: str = ""


@dataclass
class Node:
    id: str
    label: str
    kind: str = "service"
    tech: str = ""
    group: str | None = None
    tier: int | None = None
    lane: float | None = None
    replicas: int = 1
    tone: str = ""


@dataclass
class Edge:
    id: str
    src: str
    dst: str
    label: str = ""
    style: str = "sync"
    both: bool = False


@dataclass
class Flow:
    """A path through the system; each hop is an edge and whether it is run forward."""

    id: str
    label: str
    nodes: list[str]
    hops: list[tuple[Edge, bool]] = field(default_factory=list)
    tone: str = "accent"


@dataclass
class Tad:
    direction: str
    nodes: dict[str, Node]
    groups: dict[str, Group]
    edges: dict[str, Edge]
    flows: dict[str, Flow]
    legend: dict[str, str]

    def ids(self) -> set[str]:
        return {*self.nodes, *self.groups, *self.edges, *self.flows}

    def members(self, group: str) -> list[str]:
        """Every node inside a group, through nested groups too."""
        inside = {group}
        changed = True
        while changed:
            changed = False
            for g in self.groups.values():
                if g.parent in inside and g.id not in inside:
                    inside.add(g.id)
                    changed = True
        return [n.id for n in self.nodes.values() if n.group in inside]

    def chain(self, group: str | None) -> list[str]:
        """A group and every group around it, innermost first."""
        out = []
        while group is not None and group in self.groups:
            out.append(group)
            group = self.groups[group].parent
        return out


def read(spec: Any, report: Report, facts: Mapping[str, Any]) -> Tad | None:
    """Parse and check a `tad` object; problems go to the report with their path."""
    if not isinstance(spec, Mapping):
        report.errors.append("tad must be an object")
        return None
    for key in sorted(set(spec) - {"direction", "groups", "nodes", "edges", "flows", "legend"}):
        report.errors.append(f"tad.{key} is unknown; tad takes direction, groups, nodes, ...")
    direction = str(spec.get("direction", "right"))
    if direction not in DIRECTIONS:
        report.errors.append(f"tad.direction must be one of {', '.join(DIRECTIONS)}")
    seen: set[str] = set()
    groups = {g.id: g for g in _groups(spec.get("groups", []), report, seen, facts)}
    nodes = {n.id: n for n in _nodes(spec.get("nodes", []), report, seen, groups, facts)}
    if not nodes:
        report.errors.append("tad.nodes needs at least one component")
    edges = {e.id: e for e in _edges(spec.get("edges", []), report, seen, nodes, facts)}
    flows = {f.id: f for f in _flows(spec.get("flows", []), report, seen, nodes, edges, facts)}
    for g in groups.values():
        if g.parent is not None and g.parent not in groups:
            report.errors.append(f"group {g.id}: parent {g.parent!r} is not a group")
        elif g.id in _ancestors(groups, g.parent):
            report.errors.append(f"group {g.id} is inside itself through its parents")
    lanes = [n.lane is not None for n in nodes.values()]
    if any(lanes) and not all(lanes):
        report.errors.append("give every node a lane, or leave lane out on all of them")
    return Tad(direction, nodes, groups, edges, flows, _legend(spec.get("legend"), edges, report))


def _ancestors(groups: Mapping[str, Group], start: str | None) -> list[str]:
    out: list[str] = []
    while start is not None and start in groups and start not in out:
        out.append(start)
        start = groups[start].parent
    return out


def _new_id(raw: Any, where: str, report: Report, seen: set[str]) -> str | None:
    value = str(raw or "")
    if not _ID.match(value):
        report.errors.append(f"{where}.id must start with a letter: letters, digits, - and _")
        return None
    if value in seen:
        report.errors.append(f"{where}.id {value!r} is used twice; ids are shared by every part")
        return None
    seen.add(value)
    return value


def _tone(raw: Any, where: str, report: Report) -> str:
    tone = str(raw or "")
    if tone and tone not in TONES and not _TONE.match(tone):
        report.errors.append(f"{where}.tone must be one of {', '.join(TONES)} or c-<name>")
        return ""
    return tone


def _items(raw: Any, name: str, report: Report) -> list[tuple[str, Mapping[str, Any]]]:
    if not isinstance(raw, list):
        report.errors.append(f"tad.{name} must be a list")
        return []
    out = []
    for i, item in enumerate(raw):
        where = f"tad.{name}[{i}]"
        if not isinstance(item, Mapping):
            report.errors.append(f"{where} must be an object")
            continue
        out.append((where, item))
    return out


def _groups(raw: Any, report: Report, seen: set[str], facts: Mapping[str, Any]) -> list[Group]:
    out = []
    for where, item in _items(raw, "groups", report):
        gid = _new_id(item.get("id"), where, report, seen)
        style = str(item.get("style", "zone"))
        if style not in GROUP_STYLES:
            report.errors.append(f"{where}.style must be one of {', '.join(GROUP_STYLES)}")
        label = str(item.get("label", ""))
        check_text(label, f"{where}.label", "", facts, report)
        if gid:
            parent = item.get("parent")
            out.append(
                Group(
                    gid,
                    label,
                    style,
                    str(parent) if parent else None,
                    _tone(item.get("tone"), where, report),
                )
            )
    return out


def _nodes(
    raw: Any, report: Report, seen: set[str], groups: Mapping[str, Group], facts: Mapping[str, Any]
) -> list[Node]:
    out = []
    for where, item in _items(raw, "nodes", report):
        nid = _new_id(item.get("id"), where, report, seen)
        label = str(item.get("label", "")).strip()
        if not label:
            report.errors.append(f"{where}.label is required")
        kind = str(item.get("kind", "service"))
        if kind not in GLYPHS:
            near = difflib.get_close_matches(kind, list(GLYPHS), n=1)
            hint = f" (did you mean {near[0]}?)" if near else ""
            report.errors.append(f"{where}.kind {kind!r} is unknown{hint}; use {', '.join(GLYPHS)}")
        group = item.get("group")
        if group is not None and str(group) not in groups:
            report.errors.append(f"{where}.group {group!r} is not in tad.groups")
        tier = item.get("tier")
        if tier is not None and not (isinstance(tier, int) and 0 <= tier <= 20):
            report.errors.append(f"{where}.tier must be a whole number from 0 to 20")
            tier = None
        lane = item.get("lane")
        if lane is not None and not (isinstance(lane, int | float) and 0 <= lane <= 40):
            report.errors.append(f"{where}.lane must be a number from 0 to 40")
            lane = None
        replicas = item.get("replicas", 1)
        if not (isinstance(replicas, int) and 1 <= replicas <= 99):
            report.errors.append(f"{where}.replicas must be a whole number from 1 to 99")
            replicas = 1
        for key in ("label", "tech"):
            check_text(str(item.get(key, "")), f"{where}.{key}", "", facts, report)
        if nid:
            out.append(
                Node(
                    nid,
                    label,
                    kind,
                    str(item.get("tech", "")),
                    str(group) if group is not None else None,
                    tier,
                    float(lane) if lane is not None else None,
                    replicas,
                    _tone(item.get("tone"), where, report),
                )
            )
    return out


def _edges(
    raw: Any, report: Report, seen: set[str], nodes: Mapping[str, Node], facts: Mapping[str, Any]
) -> list[Edge]:
    out = []
    for where, item in _items(raw, "edges", report):
        src, dst = str(item.get("from", "")), str(item.get("to", ""))
        for end, value in (("from", src), ("to", dst)):
            if value not in nodes:
                near = difflib.get_close_matches(value, list(nodes), n=1)
                hint = f" (did you mean {near[0]}?)" if near else ""
                report.errors.append(f"{where}.{end} {value!r} is not a node{hint}")
        if src == dst and src:
            report.errors.append(f"{where} links {src} to itself")
        style = str(item.get("style", "sync"))
        if style not in EDGE_STYLES:
            report.errors.append(f"{where}.style must be one of {', '.join(EDGE_STYLES)}")
        raw_id = item.get("id") or _free(f"{src}-{dst}", seen)
        eid = _new_id(raw_id, where, report, seen)
        check_text(str(item.get("label", "")), f"{where}.label", "", facts, report)
        if eid and src in nodes and dst in nodes and src != dst:
            out.append(
                Edge(
                    eid, src, dst, str(item.get("label", "")), style, bool(item.get("both", False))
                )
            )
    return out


def _free(base: str, seen: set[str]) -> str:
    name, n = base, 2
    while name in seen:
        name, n = f"{base}-{n}", n + 1
    return name


def _flows(
    raw: Any,
    report: Report,
    seen: set[str],
    nodes: Mapping[str, Node],
    edges: Mapping[str, Edge],
    facts: Mapping[str, Any],
) -> list[Flow]:
    out = []
    for where, item in _items(raw, "flows", report):
        fid = _new_id(item.get("id"), where, report, seen)
        path = item.get("path", [])
        if not isinstance(path, list) or len(path) < 2:
            report.errors.append(f"{where}.path must list at least two node ids in order")
            continue
        flow = Flow(fid or "", str(item.get("label", "")), [str(p) for p in path])
        flow.tone = _tone(item.get("tone"), where, report) or "accent"
        check_text(flow.label, f"{where}.label", "", facts, report)
        for a, b in zip(flow.nodes, flow.nodes[1:], strict=False):
            hop = _hop(edges, a, b)
            if hop is None:
                missing = [n for n in (a, b) if n not in nodes]
                why = f"{missing[0]!r} is not a node" if missing else f"no edge links {a} and {b}"
                report.errors.append(f"{where}.path: {why}")
                break
            flow.hops.append(hop)
        if fid and len(flow.hops) == len(flow.nodes) - 1:
            out.append(flow)
    return out


def _hop(edges: Mapping[str, Edge], a: str, b: str) -> tuple[Edge, bool] | None:
    for edge in edges.values():
        if edge.src == a and edge.dst == b:
            return edge, True
    for edge in edges.values():
        if edge.src == b and edge.dst == a:
            return edge, False
    return None


def _legend(raw: Any, edges: Mapping[str, Edge], report: Report) -> dict[str, str]:
    styles = {e.style for e in edges.values()}
    words = {"sync": "Request", "async": "Event or message"}
    if raw is False:
        return {}
    if isinstance(raw, Mapping):
        for key in sorted(set(raw) - set(EDGE_STYLES)):
            report.errors.append(f"tad.legend.{key} is unknown; name sync and async")
        words.update({k: str(v) for k, v in raw.items() if k in EDGE_STYLES})
        return {k: v for k, v in words.items() if k in styles}
    if raw is True or len(styles) > 1:
        return {k: v for k, v in words.items() if k in styles}
    return {}
