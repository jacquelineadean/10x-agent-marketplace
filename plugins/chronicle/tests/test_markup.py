from __future__ import annotations

from chronicle.core.story.markup import inline, paragraphs


def fact(path: str, fmt: str) -> str:
    return f'<span class="fact">{path}|{fmt}</span>'


def test_markup_escapes_html_from_gathered_text() -> None:
    out = inline('PR title <img src=x onerror="alert(1)"> & more', fact)
    assert "<img" not in out
    assert "&lt;img src=x onerror=&quot;alert(1)&quot;&gt; &amp; more" in out


def test_links_allow_only_web_and_page_anchors() -> None:
    assert '<a href="https://example.com"' in inline("[docs](https://example.com)", fact)
    assert '<a href="#status">' in inline("[status](#status)", fact)
    assert "<a" not in inline("[x](javascript:alert(1))", fact)


def test_emphasis_and_fact_tokens() -> None:
    out = inline("**Bold** and *italic* with {{a.b|pct}}", fact)
    assert out == '<strong>Bold</strong> and <em>italic</em> with <span class="fact">a.b|pct</span>'


def test_paragraphs_split_on_blank_lines() -> None:
    assert paragraphs("One\nline.\n\nTwo.", fact) == "<p>One line.</p>\n<p>Two.</p>"
