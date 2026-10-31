"""chronicle's own commands: `motifs` lists the painter's presets and motifs."""

from __future__ import annotations

import argparse
from typing import Any


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
