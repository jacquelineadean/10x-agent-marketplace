"""chronicle's own commands: `motifs` lists the painter's presets and motifs; `research`
checks what the researcher wrote to a run folder."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from chronicle_engine.connectors.files import store

from chronicle.core.story import research as checks


def motifs_parser(sub: Any) -> None:
    sub.add_parser("motifs")


def motifs(args: argparse.Namespace) -> int:
    from chronicle.core.watercolor import presets  # needs NumPy and OpenCV
    from chronicle.core.watercolor import scene as painted

    print('Presets (art spec: {"preset": NAME, "params": {...}}):')
    for name, fn in presets.PRESETS.items():
        doc = (fn.__doc__ or "").strip().splitlines()[0]
        print(f"  {name}: {doc}")
    print('\nMotifs and brush primitives (art spec elements: {"motif": NAME, ...}):')
    for name in painted.motif_names():
        print(f"  {name}({painted.motif_signature(name)})")
    return 0


def research_parser(sub: Any) -> None:
    p = sub.add_parser("research", help="check research/facts.json and research/material.md")
    p.add_argument("folder", type=Path, help="the run folder")


def research(args: argparse.Namespace) -> int:
    folder = args.folder / "research"
    errors = checks.check_facts(store.read_json(folder / "facts.json"))
    errors += checks.check_material(store.read_text(folder / "material.md"))
    for line in errors:
        print(f"error: {line}", file=sys.stderr)
    print(f"{len(errors)} problem(s) in {folder}")
    return 1 if errors else 0
