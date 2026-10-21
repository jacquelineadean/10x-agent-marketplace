"""HTML around an animation: a figure to paste into any page, a page to open, a capture page.

The figure inlines the SVG, adds a pause control made of a checkbox and CSS (moving
content longer than five seconds needs one, WCAG 2.2.2), a caption with the sources,
and the steps as a list for readers who cannot watch it. No script: it pastes into
CMS pages, docs sites, wikis that take HTML, and claude.ai Artifacts.
"""

from __future__ import annotations

from chronicle.core.motion.model import Plan
from chronicle.core.story.html import tag, void
from chronicle.core.story.markup import plain

FIGURE_CSS = """
.chr-anim { position: relative; margin: 0 auto; }
.chr-anim > svg { display: block; width: 100%; height: auto; }
.chr-anim-hold { position: absolute; width: 1px; height: 1px; opacity: 0; }
.chr-anim-btn { position: absolute; top: 10px; right: 10px; z-index: 1; padding: 6px 11px;
  border-radius: 999px; background: rgba(20, 22, 28, .66); color: #fff; cursor: pointer;
  font: 600 12px/1 system-ui, -apple-system, "Segoe UI", sans-serif; opacity: 0;
  transition: opacity .2s; }
.chr-anim:hover .chr-anim-btn, .chr-anim-hold:focus-visible + .chr-anim-btn,
.chr-anim-hold:checked + .chr-anim-btn { opacity: 1; }
.chr-anim-hold:focus-visible + .chr-anim-btn { outline: 2px solid #fff; outline-offset: 2px; }
.chr-anim-hold:checked ~ svg, .chr-anim-hold:checked ~ svg * {
  animation-play-state: paused !important; }
.chr-anim-btn .play, .chr-anim-hold:checked + .chr-anim-btn .pause { display: none; }
.chr-anim-hold:checked + .chr-anim-btn .play { display: inline; }
.chr-anim figcaption, .chr-anim details { font: 14px/1.5 system-ui, -apple-system,
  "Segoe UI", sans-serif; color: #5b5f68; margin-top: 8px; }
.chr-anim details summary { cursor: pointer; }
@media (prefers-reduced-motion: reduce) { .chr-anim-btn { display: none; } }
"""

SEEK_CSS = (
    "html, body { margin: 0; background: transparent; }\n"
    ".chr-a, .chr-a * { animation-delay: calc(var(--seek, 0s) * -1) !important;"
    " animation-play-state: paused !important; }\n"
    ".still .chr-a, .still .chr-a * { animation: none !important; }\n"
)


def figure(plan: Plan, svg: str) -> str:
    """The HTML figure: the SVG, its pause control, caption and steps."""
    hold = f"{plan.slug}-hold"
    button = tag(
        "label",
        tag("span", "Pause", class_="pause") + tag("span", "Play", class_="play"),
        class_="chr-anim-btn",
        for_=hold,
    )
    control = void("input", type="checkbox", id=hold, class_="chr-anim-hold", aria_label="Pause")
    sources = "; ".join(
        plain(s["label"]) + (f" ({plain(s['detail'])})" if s.get("detail") else "")
        for s in plan.sources
    )
    caption = plain(plan.description) + (f" Sources: {sources}." if sources else "")
    steps = "".join(tag("li", plain(s.caption)) for s in plan.steps if s.caption)
    details = tag("details", tag("summary", "Steps") + tag("ol", steps)) if steps else ""
    body = control + button + svg.strip() + tag("figcaption", caption) + details
    return (
        tag("style", FIGURE_CSS)
        + "\n"
        + tag(
            "figure",
            body,
            class_="chr-anim",
            style=f"max-width: {plan.width}px",
            data_chronicle_animation=plan.slug,
        )
        + "\n"
    )


def page(plan: Plan, fragment: str) -> str:
    """A whole page holding the figure, to open locally or publish as an Artifact."""
    head = (
        '<meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        + tag("title", plain(plan.title))
        + tag(
            "style",
            "body { margin: 0; padding: 24px 16px; background: #ECEBE6; }\n"
            "@media (prefers-color-scheme: dark) { body { background: #121317; } }\n",
        )
    )
    body = f"<body>\n{fragment}</body>"
    return f'<!doctype html>\n<html lang="en">\n<head>{head}</head>\n{body}\n</html>\n'


def capture(svg: str) -> str:
    """A bare page the browser steps through frame by frame by setting --seek."""
    return f'<!doctype html>\n<meta charset="utf-8">\n<style>{SEEK_CSS}</style>\n{svg}'
