"""Build HTML elements with every attribute value escaped."""

from __future__ import annotations

from chronicle.core.story.markup import plain

AttrValue = str | int | float | bool | None


def attrs(values: dict[str, AttrValue]) -> str:
    """Render attributes; True is a bare attribute, None and False are left out."""
    parts = []
    for key, value in values.items():
        if value is None or value is False:
            continue
        name = key.rstrip("_").replace("_", "-")
        parts.append(f" {name}" if value is True else f' {name}="{plain(str(value))}"')
    return "".join(parts)


def tag(name: str, children: str = "", **values: AttrValue) -> str:
    """One element. Children must already be HTML; attribute values are escaped here."""
    return f"<{name}{attrs(values)}>{children}</{name}>"


def void(name: str, **values: AttrValue) -> str:
    """An element with no closing tag, such as img or input."""
    return f"<{name}{attrs(values)}>"
