"""Turn a checked story into one HTML page.

The page is static HTML for every word (readable without scripts), plus one JSON blob
that the bundled runtime script reads to draw charts, plates and interactive figures.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from chronicle.core.story import theme as theming
from chronicle.core.story.blocks import stats
from chronicle.core.story.dispatch import render_block
from chronicle.core.story.facts import TOKEN, format_value, lookup, resolve_refs
from chronicle.core.story.html import tag, void
from chronicle.core.story.markup import inline, paragraphs, plain


@dataclass
class Assets:
    """The runtime stylesheet, script and font list, read from the package by the caller.

    `files` maps each file a story names (diagram SVG, widget script or style) to its text.
    """

    css: str
    js: str
    fonts: Mapping[str, Any] = field(default_factory=dict)
    files: Mapping[str, str] = field(default_factory=dict)


@dataclass
class Page:
    """Rendered output: an artifact fragment and a standalone document."""

    fragment: str
    document: str
    art_files: list[str] = field(default_factory=list)


class Builder:
    """Shared state while one page renders: facts, figure specs and the images it uses."""

    def __init__(
        self,
        story: Mapping[str, Any],
        facts: Mapping[str, Any],
        manifest: Mapping[str, Any],
        fonts: Mapping[str, Any] | None = None,
        files: Mapping[str, str] | None = None,
    ) -> None:
        self.story = story
        self.facts = facts
        self.manifest = manifest
        self.theme = theming.build(story.get("theme"), fonts or {}, _font_needs(manifest))
        self.files: Mapping[str, str] = files or {}
        self.widgets: dict[str, str] = {}
        self.figs: dict[str, Any] = {}
        self.counter = 0
        self.art_files: list[str] = []
        self.sources: dict[str, Mapping[str, Any]] = {
            str(s["id"]): s
            for s in story.get("sources", [])
            if isinstance(s, Mapping) and "id" in s
        }

    # ---------------------------------------------------------------- text bits
    def fact(self, path: str, fmt: str) -> str:
        """A fact token as a span that names its source on hover."""
        found = lookup(self.facts, path)
        text = plain(format_value(found.value, found.unit, fmt))
        return tag(
            "span",
            text,
            class_="fact",
            tabindex="0",
            data_src=found.source or None,
            data_note=found.note or None,
        )

    def inline(self, text: Any) -> str:
        return inline(str(text), self.fact) if text else ""

    def paras(self, text: Any, css: str = "") -> str:
        return paragraphs(str(text), self.fact, css) if text else ""

    def register(self, spec: Mapping[str, Any]) -> str:
        """Store a figure spec for the script, with references and tokens filled in."""
        self.counter += 1
        fid = str(spec.get("id") or f"fig-{self.counter}")
        self.figs[fid] = self.plain_text(resolve_refs(dict(spec), self.facts))
        return fid

    def plain_text(self, node: Any) -> Any:
        """Fill fact tokens and drop emphasis marks in strings the script shows as text."""
        if isinstance(node, str):

            def fill(m: re.Match[str]) -> str:
                found = lookup(self.facts, m.group(1))
                return format_value(found.value, found.unit, m.group(2) or "auto")

            return TOKEN.sub(fill, node).replace("**", "")
        if isinstance(node, Mapping):
            return {k: self.plain_text(v) for k, v in node.items()}
        if isinstance(node, list):
            return [self.plain_text(v) for v in node]
        return node

    def heading(self, block: Mapping[str, Any]) -> str:
        parts = ""
        if block.get("title"):
            parts += tag("h3", self.inline(block["title"]), class_="fig-title")
        if block.get("subtitle"):
            parts += tag("p", self.inline(block["subtitle"]), class_="fig-sub")
        return tag("header", parts, class_="fig-head") if parts else ""

    def source_line(self, block: Mapping[str, Any], table: bool = True) -> str:
        bits = ""
        src = block.get("source")
        if src:
            label = str(self.sources.get(str(src), {}).get("label", src))
            bits += tag("span", f"Source: {plain(label)}", class_="src", data_src=str(src))
        if table:
            bits += tag(
                "button",
                "Show the numbers",
                type="button",
                class_="show-table",
                aria_expanded="false",
            )
        return tag("footer", bits, class_="fig-foot") if bits else ""

    # -------------------------------------------------------------------- plates
    def plate(self, key: str, caption: Any = "", width: str = "wide", spots: Any = None) -> str:
        """A painting: base image, moving layers, an overlay for lines, optional hotspots."""
        entry = self.manifest.get(key)
        if not entry:
            return ""
        scene = self.story.get("art", {}).get(key, {})
        w, h = int(entry["width"]), int(entry["height"])
        self.art_files.append(str(entry["file"]))
        layers = "".join(self._layer(layer, w, h) for layer in entry.get("layers", []))
        anchors = entry.get("anchors", {})
        fid = self.register(
            {
                "type": "plate",
                "art": key,
                "width": w,
                "height": h,
                "anchors": anchors,
                "spots": spots or [],
            }
        )
        spot_html, cards = self._spots(spots or [], anchors, w, h)
        base = void(
            "img",
            class_="base",
            src=str(entry["file"]),
            alt=str(scene.get("alt", "")),
            width=w,
            height=h,
            decoding="async",
        )
        overlay = tag(
            "svg",
            "".join(self._label(lab) for lab in entry.get("labels", [])),
            class_="overlay",
            viewBox=f"0 0 {w} {h}",
            preserveAspectRatio="none",
            aria_hidden="true",
        )
        stage = tag(
            "div",
            base + layers + overlay + spot_html,
            class_="stage develop",
            style=f"aspect-ratio:{w}/{h}",
        )
        cap = tag("figcaption", self.inline(caption)) if caption else ""
        cls = "plate wide" if width == "wide" else "plate inset"
        return tag(
            "figure", tag("div", stage, class_="frame") + cap + cards, class_=cls, data_fig=fid
        )

    def _label(self, lab: Mapping[str, Any]) -> str:
        """Overlay text drawn in the SVG, set live in the theme's fonts."""
        angle = float(lab.get("angle", 0))
        x, y = float(lab["x"]), float(lab["y"])
        return tag(
            "text",
            plain(str(self.plain_text(str(lab.get("text", ""))))),
            x=f"{x:.1f}",
            y=f"{y:.1f}",
            class_=f"lbl lbl-{lab.get('style', 'hand')}",
            font_size=f"{float(lab.get('size', 28)):.1f}",
            text_anchor=str(lab.get("anchor", "start")),
            fill=str(lab.get("color") or "") or None,
            font_weight=str(lab.get("weight") or "") or None,
            transform=f"rotate({angle:.1f} {x:.1f} {y:.1f})" if abs(angle) > 0.05 else None,
        )

    def _layer(self, layer: Mapping[str, Any], w: int, h: int) -> str:
        self.art_files.append(str(layer["file"]))
        x, y, lw, lh = layer["box"]
        style = (
            f"left:{100 * x / w:.3f}%;top:{100 * y / h:.3f}%;"
            f"width:{100 * lw / w:.3f}%;height:{100 * lh / h:.3f}%"
        )
        blend = " blend-normal" if layer.get("blend") == "normal" else ""
        return void(
            "img",
            class_=f"layer{blend}",
            src=str(layer["file"]),
            alt="",
            aria_hidden="true",
            data_motion=str(layer.get("motion", "none")),
            data_travel=f"{float(layer.get('travel', 0)) / h * 100:.3f}",
            style=style,
        )

    def _spots(
        self, spots: list[Mapping[str, Any]], anchors: Mapping[str, Any], w: int, h: int
    ) -> tuple[str, str]:
        if not spots:
            return "", ""
        buttons = ""
        cards = ""
        for k, spot in enumerate(spots):
            point = anchors.get(str(spot.get("anchor", "")))
            if not point:
                continue
            left = 100 * float(point[0]) / w
            top = 100 * float(point[1]) / h
            side = "side-l" if left < 50 else "side-r"
            dot = tag("span", str(k + 1), class_="spot-dot", aria_hidden="true")
            label = (
                tag("span", self.inline(spot["label"]), class_="spot-label")
                if spot.get("label")
                else ""
            )
            buttons += tag(
                "button",
                dot + label,
                type="button",
                class_=f"spot {side}",
                data_spot=k,
                aria_label=None
                if spot.get("label")
                else str(self.plain_text(str(spot.get("title", k + 1)))),
                style=f"left:{left:.2f}%;top:{top:.2f}%",
            )
            title = tag("h4", self.inline(spot.get("title", spot.get("label", ""))))
            cards += tag(
                "div",
                title + self.paras(spot.get("text", "")),
                class_="spot-card",
                data_spot=k,
                hidden=True,
            )
        return buttons, tag("div", cards, class_="spot-cards", aria_live="polite")

    # ---------------------------------------------------------------------- page
    def page(self, assets: Assets) -> Page:
        meta = self.story["meta"]
        chapters = self.story["chapters"]
        body = self._hero()
        for i, chapter in enumerate(chapters):
            head = (
                self._mark(i)
                + tag("p", self.inline(chapter.get("kicker", "")), class_="kicker")
                + tag("h2", self.inline(chapter["title"]))
            )
            if chapter.get("dek"):
                head += tag("p", self.inline(chapter["dek"]), class_="chapter-dek")
            parts = tag("header", head, class_="chapter-head col")
            if chapter.get("art"):
                parts += self.plate(str(chapter["art"]), chapter.get("caption", ""))
            parts += "".join(render_block(self, b) for b in chapter.get("blocks", []))
            body += tag("section", parts, class_="chapter", id=str(chapter["id"]), data_ch=i)
        body += self._sources()
        nav = []
        for i, ch in enumerate(chapters):
            item: dict[str, Any] = {
                "id": str(ch["id"]),
                "title": str(self.plain_text(str(ch.get("short", ch["title"])))),
                "no": self.theme.number(i),
            }
            if "at" in ch:
                item["at"] = float(ch["at"])
            nav.append(item)
        data = {
            "figs": self.figs,
            "nav": nav,
            "progress": self.theme.progress,
            "sources": {
                k: {
                    "label": str(v.get("label", k)),
                    "detail": self.plain_text(str(v.get("detail", ""))),
                    "asOf": str(v.get("as_of", "")),
                }
                for k, v in self.sources.items()
            },
        }
        # Escape markup characters so no string in the data can end the script element.
        payload = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        for char, code in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
            payload = payload.replace(char, code)
        title = plain(str(meta.get("title_tag", meta["title"])))
        description = plain(str(meta.get("description", meta.get("dek", ""))))
        head_html = (
            f"<title>{title}</title>\n"
            '<meta name="claude:viewport-fit-sides" content="cover">\n'
            f'<meta name="description" content="{description}">\n'
            '<link rel="preconnect" href="https://fonts.googleapis.com">\n'
            '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
            f'<link rel="stylesheet" href="{plain(self.theme.fonts_url)}">\n'
            f"<style>\n{assets.css}\n{self.theme.css}{self._widget_css()}</style>\n"
        )
        content = (
            f"{self._bar(title)}"
            + tag("main", body, class_="story", id="top")
            + "\n"
            + f'<script type="application/json" id="chronicle-data">{payload}</script>\n'
            + "".join(
                f"<script>\n{_widget_script(name, self.files[path])}\n</script>\n"
                for name, path in self.widgets.items()
            )
            + f"<script>\n{assets.js}\n</script>\n"
        )
        document = (
            '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, '
            'viewport-fit=cover">\n'
            f"{head_html}</head>\n<body>\n{content}</body>\n</html>\n"
        )
        return Page(
            fragment=head_html + content,
            document=document,
            art_files=sorted(set(self.art_files)),
        )

    def _widget_css(self) -> str:
        """Stylesheets of the widgets on this page, after the theme so they can use its tokens."""
        css = ""
        for _, block in _blocks(self.story, "widget"):
            path = block.get("style")
            if path and str(path) in self.files:
                css += f"\n/* widget {plain(str(block['name']))} */\n{self.files[str(path)]}\n"
        return css.replace("</style", "<\\/style")

    def _mark(self, i: int) -> str:
        """The chapter number in the theme's style: an arch, a parcel label, a hang tag."""
        mark = self.theme.mark
        if mark["style"] == "none":
            return ""
        prefix = tag("span", plain(mark["prefix"]), class_="mk-pre") if mark["prefix"] else ""
        return tag(
            "p",
            prefix + tag("span", plain(self.theme.number(i)), class_="mk-n"),
            class_=f"mark mark-{mark['style']}",
            aria_hidden="true",
        )

    def _hero(self) -> str:
        meta = self.story["meta"]
        hero = self.story.get("hero", {})
        byline = "".join(tag("span", self.inline(b)) for b in meta.get("byline", []))
        intro = (
            tag("p", self.inline(meta.get("kicker", "")), class_="kicker")
            + tag("h1", self.inline(meta["title"]))
            + tag("p", self.inline(meta.get("dek", "")), class_="dek")
            + tag("p", byline, class_="byline")
        )
        style = str(hero.get("stats_style", self.theme.stats))
        figures = ""
        if hero.get("stats"):
            figures = stats(
                self,
                {
                    "items": hero["stats"],
                    "style": style,
                    "title": hero.get("stats_title", ""),
                    "subtitle": hero.get("stats_subtitle", ""),
                },
            )
        if figures and style in ("receipt", "ticket"):
            html = tag("div", tag("div", intro, class_="hero-intro") + figures, class_="hero-grid")
            figures = ""
        else:
            html = tag("div", intro, class_="col")
        if hero.get("art"):
            html += self.plate(str(hero["art"]), hero.get("caption", ""))
        return tag("header", html + figures, class_="hero")

    @staticmethod
    def _bar(title: str) -> str:
        inner = (
            f'<a class="spanbar-title" href="#top">{title}</a>'
            + tag("div", class_="spanbar-track", role="list")
            + tag("p", class_="spanbar-now", aria_live="polite")
            + tag(
                "button",
                type="button",
                class_="theme-btn",
                aria_label="Switch light or dark theme",
            )
        )
        return tag(
            "nav", tag("div", inner, class_="spanbar-in"), class_="spanbar", aria_label="Chapters"
        )

    def _sources(self) -> str:
        items = ""
        for sid, src in self.sources.items():
            as_of = src.get("as_of")
            items += tag(
                "li",
                tag("span", self.inline(src.get("label", sid)), class_="src-label")
                + (tag("span", f"as of {plain(str(as_of))}", class_="as-of") if as_of else "")
                + tag("span", self.inline(src.get("detail", "")), class_="src-detail"),
                id=f"src-{sid}",
            )
        colophon = self.paras(self.story["meta"].get("colophon", ""), "colophon")
        return tag(
            "footer",
            tag("h2", "Sources and method", class_="sources-title")
            + tag("ul", items, class_="src-list")
            + colophon,
            class_="sources col",
            id="sources",
        )


def _blocks(story: Mapping[str, Any], kind: str) -> list[tuple[int, Mapping[str, Any]]]:
    out = []
    for i, chapter in enumerate(story.get("chapters", [])):
        for block in chapter.get("blocks", []):
            if isinstance(block, Mapping) and block.get("type") == kind:
                out.append((i, block))
    return out


def _font_needs(manifest: Mapping[str, Any]) -> frozenset[str]:
    """Optional font roles the paintings' overlay text uses."""
    styles = {
        str(lab.get("style", "hand"))
        for entry in manifest.values()
        if isinstance(entry, Mapping)
        for lab in entry.get("labels", [])
    }
    needs = set()
    if "hand" in styles:
        needs.add("hand")
    if styles & {"mono", "number"}:
        needs.add("mono")
    return frozenset(needs)


def _widget_script(name: str, source: str) -> str:
    """Wrap a widget's script so it registers itself for the runtime to start."""
    safe = json.dumps(name)
    body = source.replace("</script", "<\\/script")
    return (
        "(window.chronicleWidgets = window.chronicleWidgets || {})"
        f"[{safe}] = function (root, data, kit) {{\n'use strict';\n{body}\n}};"
    )


def render(
    story: Mapping[str, Any],
    facts: Mapping[str, Any],
    manifest: Mapping[str, Any],
    assets: Assets,
) -> Page:
    """Render a story; call model.check first, since this assumes a valid story."""
    return Builder(story, facts, manifest, assets.fonts, assets.files).page(assets)
