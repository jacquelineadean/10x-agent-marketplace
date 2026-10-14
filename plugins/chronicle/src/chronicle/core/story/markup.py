"""A small, safe inline markup for story prose.

Supported: blank-line paragraphs, **bold**, *italic*, `code`, [text](https://link) and
fact tokens {{path|format}}. Everything else is escaped, so text gathered from Jira
titles or GitHub comments can never inject markup into the page.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

from chronicle.core.story.facts import TOKEN

LINK = re.compile(r"\[([^\]\n]+)\]\((https?://[^\s)]+|#[A-Za-z0-9_\-]+)\)")
BOLD = re.compile(r"\*\*(.+?)\*\*")
ITALIC = re.compile(r"(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])")
CODE = re.compile(r"`([^`\n]+)`")

FactRenderer = Callable[[str, str], str]


def inline(text: str, fact: FactRenderer) -> str:
    """Render one line or paragraph of story text to HTML."""
    saved: list[str] = []

    def keep(fragment: str) -> str:
        saved.append(fragment)
        return f"\x00{len(saved) - 1}\x00"

    with_facts = TOKEN.sub(lambda m: keep(fact(m.group(1), m.group(2) or "auto")), text)
    escaped = html.escape(with_facts, quote=True)
    escaped = CODE.sub(lambda m: keep(f"<code>{m.group(1)}</code>"), escaped)

    def link(m: re.Match[str]) -> str:
        href = m.group(2)
        external = href.startswith("http")
        attrs = ' target="_blank" rel="noopener noreferrer"' if external else ""
        return keep(f'<a href="{href}"{attrs}>{m.group(1)}</a>')

    escaped = LINK.sub(link, escaped)
    escaped = BOLD.sub(r"<strong>\1</strong>", escaped)
    escaped = ITALIC.sub(r"<em>\1</em>", escaped)
    while "\x00" in escaped:
        escaped = re.sub(r"\x00(\d+)\x00", lambda m: saved[int(m.group(1))], escaped)
    return escaped


def paragraphs(text: str, fact: FactRenderer, css_class: str = "") -> str:
    """Render blank-line separated paragraphs."""
    attr = f' class="{css_class}"' if css_class else ""
    blocks = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    return "\n".join(f"<p{attr}>{inline(' '.join(p.split()), fact)}</p>" for p in blocks)


def plain(text: str) -> str:
    """Escape text for an attribute or a text node."""
    return html.escape(text, quote=True)
