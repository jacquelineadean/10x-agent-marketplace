"""Tile-grid layouts for tile maps: every region an equal square, placed roughly where it is.

A tile map trades exact geography for equal weight, so a small state with many stores
reads as clearly as a large empty one.
"""

from __future__ import annotations

US_STATES: tuple[tuple[str, str, int, int], ...] = (
    ("AK", "Alaska", 0, 0),
    ("ME", "Maine", 0, 11),
    ("VT", "Vermont", 1, 10),
    ("NH", "New Hampshire", 1, 11),
    ("WA", "Washington", 2, 1),
    ("ID", "Idaho", 2, 2),
    ("MT", "Montana", 2, 3),
    ("ND", "North Dakota", 2, 4),
    ("MN", "Minnesota", 2, 5),
    ("WI", "Wisconsin", 2, 6),
    ("MI", "Michigan", 2, 7),
    ("NY", "New York", 2, 9),
    ("MA", "Massachusetts", 2, 10),
    ("RI", "Rhode Island", 2, 11),
    ("OR", "Oregon", 3, 1),
    ("NV", "Nevada", 3, 2),
    ("WY", "Wyoming", 3, 3),
    ("SD", "South Dakota", 3, 4),
    ("IA", "Iowa", 3, 5),
    ("IL", "Illinois", 3, 6),
    ("IN", "Indiana", 3, 7),
    ("OH", "Ohio", 3, 8),
    ("PA", "Pennsylvania", 3, 9),
    ("NJ", "New Jersey", 3, 10),
    ("CT", "Connecticut", 3, 11),
    ("CA", "California", 4, 1),
    ("UT", "Utah", 4, 2),
    ("CO", "Colorado", 4, 3),
    ("NE", "Nebraska", 4, 4),
    ("MO", "Missouri", 4, 5),
    ("KY", "Kentucky", 4, 6),
    ("WV", "West Virginia", 4, 7),
    ("VA", "Virginia", 4, 8),
    ("MD", "Maryland", 4, 9),
    ("DE", "Delaware", 4, 10),
    ("AZ", "Arizona", 5, 2),
    ("NM", "New Mexico", 5, 3),
    ("KS", "Kansas", 5, 4),
    ("AR", "Arkansas", 5, 5),
    ("TN", "Tennessee", 5, 6),
    ("NC", "North Carolina", 5, 7),
    ("SC", "South Carolina", 5, 8),
    ("DC", "District of Columbia", 5, 9),
    ("OK", "Oklahoma", 6, 4),
    ("LA", "Louisiana", 6, 5),
    ("MS", "Mississippi", 6, 6),
    ("AL", "Alabama", 6, 7),
    ("GA", "Georgia", 6, 8),
    ("HI", "Hawaii", 7, 1),
    ("TX", "Texas", 7, 4),
    ("FL", "Florida", 7, 9),
)


def tiles(layout: str) -> list[dict[str, str | int]]:
    """A built-in layout as tile records: id, label, row, col."""
    if layout == "us-states":
        return [{"id": a, "label": n, "row": r, "col": c} for a, n, r, c in US_STATES]
    raise ValueError(f"unknown tile layout {layout!r}; use us-states or custom tiles")
