"""Named watercolor pigments.

Each value is the color a full-strength wash leaves on white paper. Washes multiply onto
the paper, so overlapping washes glaze the way transparent watercolor does.
"""

from __future__ import annotations

PIGMENTS: dict[str, str] = {
    "ultramarine": "#3d55a6",
    "cobalt": "#3f6fc0",
    "cerulean": "#4c93c4",
    "prussian": "#23415e",
    "indigo": "#2d3550",
    "paynes-grey": "#4a5565",
    "neutral-tint": "#5a5a62",
    "lavender": "#8f86b8",
    "cobalt-teal": "#3aa395",
    "viridian": "#2f7a69",
    "sap-green": "#6f8f3c",
    "hookers-green": "#3e6b45",
    "olive": "#7d7a3c",
    "lemon": "#ead25a",
    "gamboge": "#e6b23c",
    "yellow-ochre": "#d4a24c",
    "raw-sienna": "#c8893a",
    "burnt-sienna": "#ad532e",
    "burnt-umber": "#6c4a34",
    "sepia": "#4b3b2f",
    "vermilion": "#d6512f",
    "cadmium-orange": "#e3803a",
    "rose": "#cf5f7a",
    "madder": "#a63d4f",
    "warm-grey": "#9a9187",
    "ink": "#2b231d",
    "graphite": "#6b6a68",
}


def pigment_rgb(name_or_hex: str) -> tuple[float, float, float]:
    """Return a pigment as RGB floats in [0, 1]; accepts a pigment name or a #rrggbb hex."""
    value = PIGMENTS.get(name_or_hex, name_or_hex)
    if not (value.startswith("#") and len(value) == 7):
        known = ", ".join(sorted(PIGMENTS))
        raise ValueError(f"unknown pigment {name_or_hex!r}; use #rrggbb or one of: {known}")
    try:
        red, green, blue = (int(value[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    except ValueError as exc:
        raise ValueError(f"bad hex color {value!r}") from exc
    return (red, green, blue)
