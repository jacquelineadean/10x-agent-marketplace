"""A TAD animation from a table's Unity Catalog lineage: the tables it is built from, the
table, and the tables built from it, grouped by schema, with data flowing in then out."""

from __future__ import annotations

from typing import Any

MOST = 12


def _schema(name: str) -> str:
    return name.rsplit(".", 1)[0] if "." in name else "tables"


def animation(table: str, upstream: list[str], downstream: list[str], as_of: str) -> dict[str, Any]:
    """An animation.json for the `tad` kind; at most 12 tables on each side.

    Ids are short (`t1`, `s1`, `e1`) because TAD ids stop at 41 characters; labels carry
    the names.
    """
    ups, downs = upstream[:MOST], downstream[:MOST]
    names = list(dict.fromkeys([*ups, table, *downs]))
    ids = {name: f"t{k}" for k, name in enumerate(names, 1)}
    schemas = {s: f"s{k}" for k, s in enumerate(dict.fromkeys(_schema(n) for n in names), 1)}
    groups = [{"id": sid, "label": s, "style": "cluster"} for s, sid in schemas.items()]
    nodes = [
        {"id": ids[n], "label": n.rsplit(".", 1)[-1], "kind": "db", "group": schemas[_schema(n)]}
        for n in names
    ]
    centre = ids[table]
    pairs = [(ids[u], centre) for u in ups] + [(centre, ids[d]) for d in downs]
    edges = [{"id": f"e{k}", "from": a, "to": b} for k, (a, b) in enumerate(pairs, 1)]
    ins = [f"in-{k}" for k in range(1, len(ups) + 1)]
    outs = [f"out-{k}" for k in range(1, len(downs) + 1)]
    flows: list[dict[str, Any]] = [
        {"id": i, "path": [ids[u], centre]} for i, u in zip(ins, ups, strict=True)
    ]
    flows += [{"id": o, "path": [centre, ids[d]]} for o, d in zip(outs, downs, strict=True)]
    more = len(upstream) - len(ups) + len(downstream) - len(downs)
    short = table.rsplit(".", 1)[-1]
    first = f"{short} is built from the tables on its left." if ups else f"{short} has no sources."
    steps = [{"caption": first, "show": [ids[u] for u in ups] + [centre], "flow": ins}]
    if downs:
        steps.append(
            {
                "caption": f"The tables on the right read {short}.",
                "show": [ids[d] for d in downs],
                "flow": outs,
            }
        )
    note = f" {more} more tables are left out." if more else ""
    return {
        "schema_version": 1,
        "kind": "tad",
        "meta": {
            "title": f"Where {short} comes from and goes",
            "kicker": "Data lineage",
            "description": f"Unity Catalog lineage of {table}: the tables it is built from and "
            f"the tables built from it.{note}",
            "credit": "Unity Catalog",
            "sources": [{"label": "Databricks Unity Catalog", "detail": f"table lineage, {as_of}"}],
        },
        "theme": {
            "concept": "A data lineage map: graphite ink on pale paper, one accent for data."
        },
        "frame": {"size": "16:9"},
        "tad": {
            "direction": "right",
            "groups": groups,
            "nodes": nodes,
            "edges": edges,
            "flows": flows,
        },
        "steps": steps,
    }
