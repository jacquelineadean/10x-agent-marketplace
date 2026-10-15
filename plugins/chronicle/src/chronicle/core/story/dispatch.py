"""One table from block type to renderer, across the block modules."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import TYPE_CHECKING, Any

from chronicle.core.story import blocks, explainers, lessons

if TYPE_CHECKING:
    from chronicle.core.story.render import Builder

RENDERERS: dict[str, Callable[[Builder, Mapping[str, Any]], str]] = {
    **blocks.RENDERERS,
    **explainers.RENDERERS,
    **lessons.RENDERERS,
}


def render_block(b: Builder, block: Mapping[str, Any]) -> str:
    """Render one block; model.check has already validated its type."""
    return RENDERERS[str(block["type"])](b, block)
