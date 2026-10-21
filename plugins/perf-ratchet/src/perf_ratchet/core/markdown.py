"""A small Markdown to HTML converter for the write-up section of the dashboard.

Covers what the writer is told to use: headings, paragraphs, lists, tables, quotes, code
blocks, bold, italics, code spans and http(s) links. Every piece of text is escaped first.
"""

from __future__ import annotations

import re
from html import escape

_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+)\)")
_BOLD = re.compile(r"\*\*(.+?)\*\*")
_ITALIC = re.compile(r"(?<![*\w])\*(?!\s)(.+?)(?<!\s)\*(?![*\w])")
_CODE = re.compile(r"`([^`]+)`")
_COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)
_ORDERED = re.compile(r"^\d+\.\s+")


def to_html(markdown: str) -> str:
    lines = _COMMENT.sub("", markdown).splitlines()
    out: list[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
        elif stripped.startswith("```"):
            i = _code_block(lines, i, out)
        elif stripped.startswith("#"):
            level = min(len(stripped) - len(stripped.lstrip("#")), 4)
            out.append(f"<h{level + 1}>{inline(stripped[level:].strip())}</h{level + 1}>")
            i += 1
        elif stripped.startswith("|"):
            i = _table(lines, i, out)
        elif stripped.startswith(("- ", "* ")):
            i = _list(lines, i, out, ordered=False)
        elif _ORDERED.match(stripped):
            i = _list(lines, i, out, ordered=True)
        elif stripped.startswith(">"):
            quote: list[str] = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(f"<blockquote><p>{inline(' '.join(quote))}</p></blockquote>")
        else:
            para: list[str] = []
            while i < len(lines) and lines[i].strip() and not _starts_block(lines[i].strip()):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
    return "\n".join(out)


def inline(text: str) -> str:
    """Escape, then apply code spans, links, bold and italics; code spans are left literal."""
    spans: list[str] = []

    def keep(match: re.Match[str]) -> str:
        spans.append(f"<code>{escape(match.group(1))}</code>")
        return f"\x00{len(spans) - 1}\x00"

    text = _CODE.sub(keep, text)
    text = escape(text)
    text = _LINK.sub(
        lambda m: (
            f'<a href="{m.group(2)}" rel="noopener noreferrer" target="_blank">{m.group(1)}</a>'
        ),
        text,
    )
    text = _BOLD.sub(r"<strong>\1</strong>", text)
    text = _ITALIC.sub(r"<em>\1</em>", text)
    return re.sub(r"\x00(\d+)\x00", lambda m: spans[int(m.group(1))], text)


def _starts_block(stripped: str) -> bool:
    return (
        stripped.startswith(("#", "|", "- ", "* ", ">", "```"))
        or _ORDERED.match(stripped) is not None
    )


def _code_block(lines: list[str], i: int, out: list[str]) -> int:
    body: list[str] = []
    i += 1
    while i < len(lines) and not lines[i].strip().startswith("```"):
        body.append(lines[i])
        i += 1
    out.append(f"<pre><code>{escape(chr(10).join(body))}</code></pre>")
    return i + 1


def _list(lines: list[str], i: int, out: list[str], ordered: bool) -> int:
    items: list[str] = []
    while i < len(lines):
        stripped = lines[i].strip()
        if ordered and _ORDERED.match(stripped):
            items.append(_ORDERED.sub("", stripped))
        elif not ordered and stripped.startswith(("- ", "* ")):
            items.append(stripped[2:])
        elif stripped and lines[i].startswith((" ", "\t")) and items:
            items[-1] += " " + stripped
        else:
            break
        i += 1
    tag = "ol" if ordered else "ul"
    out.append(f"<{tag}>" + "".join(f"<li>{inline(item)}</li>" for item in items) + f"</{tag}>")
    return i


def _table(lines: list[str], i: int, out: list[str]) -> int:
    rows: list[list[str]] = []
    while i < len(lines) and lines[i].strip().startswith("|"):
        cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
        if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells if c):
            rows.append(cells)
        i += 1
    if not rows:
        return i
    head = "".join(f"<th>{inline(c)}</th>" for c in rows[0])
    body = "".join(
        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>" for row in rows[1:]
    )
    out.append(
        f'<div class="table-scroll"><table><thead><tr>{head}</tr></thead>'
        f"<tbody>{body}</tbody></table></div>"
    )
    return i
