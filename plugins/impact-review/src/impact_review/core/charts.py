"""Inline SVG bar charts for the offline dashboard. No scripts, no external files."""

from __future__ import annotations

from html import escape

BAR_HEIGHT = 18
LABEL_WIDTH = 110
CHART_WIDTH = 640


def bar_chart(title: str, items: list[tuple[str, int]], color: str = "#2f6fdb") -> str:
    """Horizontal bars, one per item, widths scaled to the largest value."""
    rows = items or [("none", 0)]
    peak = max(value for _, value in rows) or 1
    height = BAR_HEIGHT * len(rows) + 30
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CHART_WIDTH}" height="{height}" '
        f'role="img" aria-label="{escape(title)}">',
        f'<text x="0" y="14" font-size="13" font-weight="bold">{escape(title)}</text>',
    ]
    bar_space = CHART_WIDTH - LABEL_WIDTH - 60
    for index, (label, value) in enumerate(rows):
        y = 24 + index * BAR_HEIGHT
        width = int(bar_space * value / peak)
        parts.append(
            f'<text x="0" y="{y + 13}" font-size="11">{escape(str(label))}</text>'
            f'<rect x="{LABEL_WIDTH}" y="{y + 2}" width="{width}" height="{BAR_HEIGHT - 4}" '
            f'fill="{color}" />'
            f'<text x="{LABEL_WIDTH + width + 4}" y="{y + 13}" font-size="11">{value}</text>'
        )
    parts.append("</svg>")
    return "".join(parts)
