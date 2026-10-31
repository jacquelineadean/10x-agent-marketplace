"""The `erd` kind: tables, their key columns and how they relate.

Claude writes entities with columns, or `blueprint schema` writes them from a schema
export; code places the tables in a grid, joins related columns with elbow lines and
marks each end: a bar for one, a crow's foot for many.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from chronicle_engine.core.story.model import Report

from blueprint.core import drawn

WIDTH = 960
BOX_W = 200
HEAD = 30
ROW = 20
GAP_X = 60
GAP_Y = 40
CARDINALITY = ("one-to-one", "one-to-many", "many-to-one", "many-to-many")
SKELETON = {
    "entities": [
        {"id": "customers", "columns": [{"name": "id", "type": "bigint", "key": "pk"}]},
        {
            "id": "orders",
            "columns": [
                {"name": "id", "type": "bigint", "key": "pk"},
                {"name": "customer_id", "type": "bigint", "key": "fk"},
            ],
        },
    ],
    "relations": [{"from": "orders.customer_id", "to": "customers.id", "kind": "many-to-one"}],
}


def _columns(spec: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        str(e["id"]): [str(c.get("name")) for c in e.get("columns", []) if isinstance(c, Mapping)]
        for e in spec.get("entities", [])
        if isinstance(e, Mapping) and e.get("id")
    }


def validate(spec: Mapping[str, Any], report: Report) -> None:
    entities = spec.get("entities")
    if not isinstance(entities, list) or not entities:
        report.errors.append("erd.entities needs at least one {id, columns}")
        return
    ids = [str(e.get("id", "")) for e in entities if isinstance(e, Mapping)]
    if len(set(ids)) != len(ids) or "" in ids:
        report.errors.append("erd.entities each need a unique id")
    known = _columns(spec)
    for k, r in enumerate(spec.get("relations", [])):
        for end in ("from", "to"):
            table, _, column = str(r.get(end, "")).partition(".")
            if column not in known.get(table, []):
                report.errors.append(f"erd.relations[{k}].{end} must name table.column")
        if r.get("kind", "many-to-one") not in CARDINALITY:
            report.errors.append(f"erd.relations[{k}].kind must be one of {', '.join(CARDINALITY)}")


@dataclass(frozen=True)
class Grid:
    """Where each table sits: its column, row and box, and the bounds of every row."""

    cells: dict[str, tuple[int, int, float, float, float]]
    rows: list[tuple[float, float]]
    left: float
    height: float

    def col_x(self, col: int) -> float:
        return self.left + col * (BOX_W + GAP_X)

    def channel(self, col: int, side: int) -> float:
        """The x of the gap beside a column, on its right (1) or left (-1)."""
        return self.col_x(col) + (BOX_W + GAP_X / 2 if side > 0 else -GAP_X / 2)

    def gap(self, row: int, below: bool) -> float:
        """The y of the gap under (or over) a row."""
        top, bottom = self.rows[row]
        return bottom + GAP_Y / 2 if below else top - GAP_Y / 2


def _place(spec: Mapping[str, Any]) -> Grid:
    """Tables in rows as wide as the frame allows, every row as tall as its tallest table."""
    entities = list(spec["entities"])
    per_row = max(1, min(len(entities), int((WIDTH + GAP_X) // (BOX_W + GAP_X))))
    per_row = min(per_row, math.ceil(math.sqrt(len(entities) * 2)))
    width = per_row * BOX_W + (per_row - 1) * GAP_X
    left = (WIDTH - width) / 2
    cells: dict[str, tuple[int, int, float, float, float]] = {}
    rows: list[tuple[float, float]] = []
    y = GAP_Y / 2 + 6
    for r, start in enumerate(range(0, len(entities), per_row)):
        row = entities[start : start + per_row]
        tallest = 0.0
        for c, e in enumerate(row):
            h = HEAD + ROW * len(e.get("columns", [])) + 8
            cells[str(e["id"])] = (c, r, left + c * (BOX_W + GAP_X), y, h)
            tallest = max(tallest, h)
        rows.append((y, y + tallest))
        y += tallest + GAP_Y
    return Grid(cells, rows, left, y - GAP_Y / 2 + 6)


def _route(
    grid: Grid, a: str, ya: float, b: str, yb: float, lane: float
) -> tuple[str, float, float, int, int]:
    """An elbow path from table a's row ya to table b's row yb that runs only in the gaps.

    It leaves a by the side facing b, follows the gap beside a, crosses in the gap between
    rows when it has to, and enters b from the side facing a. Returns the path, both end
    points' x and the side each end leaves by.
    """
    ca, ra = grid.cells[a][:2]
    cb, rb = grid.cells[b][:2]
    sa = 1 if cb >= ca else -1
    sb = 1 if ca >= cb else -1
    xa = grid.col_x(ca) + (BOX_W if sa > 0 else 0)
    xb = grid.col_x(cb) + (BOX_W if sb > 0 else 0)
    cha = grid.channel(ca, sa) + lane
    chb = grid.channel(cb, sb) + lane
    if abs(cha - chb) < 1:
        path = f"M{xa:g} {ya:g} L{cha:g} {ya:g} L{cha:g} {yb:g} L{xb:g} {yb:g}"
    else:
        below = rb > ra or (rb == ra and ra < len(grid.rows) - 1)
        gy = grid.gap(ra, below) + lane
        path = (
            f"M{xa:g} {ya:g} L{cha:g} {ya:g} L{cha:g} {gy:g} "
            f"L{chb:g} {gy:g} L{chb:g} {yb:g} L{xb:g} {yb:g}"
        )
    return path, xa, xb, sa, sb


def _end(x: float, y: float, side: float, many: bool) -> str:
    """The mark at one end of a relation, just outside the table: a crow's foot or a bar."""
    if many:
        return (
            f'<path class="line" d="M{x + 12 * side:g} {y - 6:g} L{x:g} {y:g} '
            f'L{x + 12 * side:g} {y + 6:g} M{x:g} {y:g} L{x + 12 * side:g} {y:g}"/>'
        )
    return f'<path class="line" d="M{x + 8 * side:g} {y - 6:g} L{x + 8 * side:g} {y + 6:g}"/>'


def draw(spec: Mapping[str, Any]) -> str:
    grid = _place(spec)
    known = _columns(spec)
    parts = ""
    for e in spec["entities"]:
        eid = str(e["id"])
        _, _, x, y, h = grid.cells[eid]
        rows = ""
        for i, c in enumerate(e.get("columns", [])):
            key = {"pk": "PK ", "fk": "FK "}.get(str(c.get("key", "")), "")
            line_y = y + HEAD + 15 + ROW * i
            rows += drawn.text("small", x + 10, line_y, key + str(c.get("name", "")))
            rows += drawn.text("small", x + BOX_W - 10, line_y, c.get("type", ""), "end")
        parts += (
            f'<g id="e-{eid}">'
            f'<rect class="box" x="{x:g}" y="{y:g}" width="{BOX_W}" height="{h:g}" rx="6"/>'
            f'<path class="line" d="M{x:g} {y + HEAD:g} L{x + BOX_W:g} {y + HEAD:g}"/>'
            + drawn.text("title", x + 10, y + 20, e.get("label", eid))
            + f"{rows}</g>"
        )
    for k, r in enumerate(spec.get("relations", [])):
        (ta, ca), (tb, cb) = (str(r[end]).split(".", 1) for end in ("from", "to"))
        ya = grid.cells[ta][3] + HEAD + 11 + ROW * known[ta].index(ca)
        yb = grid.cells[tb][3] + HEAD + 11 + ROW * known[tb].index(cb)
        lane = (k % 5 - 2) * 5.0
        path, xa, xb, sa, sb = _route(grid, ta, ya, tb, yb, lane)
        kind = str(r.get("kind", "many-to-one"))
        label = (
            drawn.text("label", xa + 16 * sa, ya - 5, r["label"], "start" if sa > 0 else "end")
            if r.get("label")
            else ""
        )
        parts += (
            f'<g id="r{k + 1}"><path id="r{k + 1}-path" class="line" d="{path}"/>'
            f"{_end(xa, ya, sa, kind.startswith('many'))}{_end(xb, yb, sb, kind.endswith('many'))}"
            f"{label}</g>"
        )
    return drawn.svg(WIDTH, grid.height, parts)


def default_steps(spec: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The tables first, then the relations that join them."""
    tables = [f"e-{e['id']}" for e in spec["entities"]]
    names = ", ".join(str(e.get("label", e["id"])) for e in spec["entities"])
    steps: list[dict[str, Any]] = [{"caption": f"Tables: {names}.", "show": tables}]
    relations = [f"r{k + 1}" for k in range(len(spec.get("relations", [])))]
    if relations:
        steps.append({"caption": "Keys join the tables.", "draw": relations})
    return steps


ERD = drawn.kind(
    "erd",
    draw,
    validate,
    default_steps,
    SKELETON,
    "write the entities and their key columns, and the relations; or run `schema`",
)
