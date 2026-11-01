"""What a collector returns, and the checks every request object shares.

A queries entry for the script lane holds a `request`: what to read, in the shape the
system's recipe gives. A collector turns it into one value or a table of columns and the
text of the query it ran, which `queries.json` keeps.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from sources.core.periods import PERS, Window, periods

Number = int | float | None


class RequestError(ValueError):
    """A request object a collector cannot run, naming the key to fix."""


@dataclass
class Result:
    """One value, or columns of equal length; `query` is the text written to queries.json."""

    query: str
    value: Any = None
    table: dict[str, list[Any]] | None = None
    warnings: list[str] = field(default_factory=list)

    @property
    def size(self) -> str:
        if self.table is None:
            return "1 value"
        rows = max((len(v) for v in self.table.values()), default=0)
        return f"{rows} row{'s' if rows != 1 else ''} x {len(self.table)} columns"


def text(request: Mapping[str, Any], key: str, limit: int = 500, required: bool = True) -> str:
    """A one-line text field of at most `limit` characters."""
    value = request.get(key)
    if value is None and not required:
        return ""
    if not isinstance(value, str) or not value.strip():
        raise RequestError(f"request.{key} must be text")
    if len(value) > limit or any(c in value for c in "\n\r\0"):
        raise RequestError(f"request.{key} must be one line of at most {limit} characters")
    return value.strip()


def field_name(request: Mapping[str, Any], key: str, default: str) -> str:
    """A field or column name: letters, digits, _ and . only."""
    value = request.get(key, default)
    if not isinstance(value, str) or not re.match(r"^[A-Za-z_][A-Za-z0-9_.]{0,79}$", value):
        raise RequestError(f"request.{key} must be a field name such as {default!r}")
    return value


def choice(request: Mapping[str, Any], key: str, options: tuple[str, ...], default: str) -> str:
    value = request.get(key, default)
    if value not in options:
        raise RequestError(f"request.{key} must be one of {', '.join(options)}")
    return str(value)


def per(request: Mapping[str, Any]) -> str:
    """The period of a series, or '' for one value over the window."""
    value = request.get("per", "")
    if value and value not in PERS:
        raise RequestError(f"request.per must be one of {', '.join(PERS)}")
    return str(value or "")


def only(request: Mapping[str, Any], allowed: set[str]) -> None:
    """Refuse keys a collector does not read, so a typo never passes silently."""
    extra = sorted(set(request) - allowed - {"per", "unit", "note"})
    if extra:
        raise RequestError(f"request.{extra[0]} is not read here; use {', '.join(sorted(allowed))}")


def measured(
    span: Window, every: str, name: str, measure: Callable[[Window], Number]
) -> tuple[Number, dict[str, list[Any]] | None]:
    """One measure over the window, or one per period with the period labels beside it."""
    if not every:
        return measure(span), None
    slices = periods(span, every)
    return None, {every: [p.label for p in slices], name: [measure(p.window) for p in slices]}
