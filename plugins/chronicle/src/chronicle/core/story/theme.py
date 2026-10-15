"""A page's visual identity: colors, type, the progress device and chapter marks.

The story's `theme` names a few brand colors and fonts; code derives the rest (text-safe
accent shades, washes, a sequential ramp, every dark-mode color) and checks contrast,
so a theme written in a minute still reads well in both light and dark.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

RGB = tuple[float, float, float]

LIGHT = {
    "paper": "#FBFAF6",
    "ink": "#1E2026",
    "accent": "#3358B5",
    "legacy": "#BD5B2D",
    "good": "#2F7D4F",
    "warn": "#9C6210",
    "bad": "#B23A2B",
}
DARK = {"paper": "#15171C", "ink": "#ECE9E2"}
SERIES = ("#3358B5", "#BD5B2D", "#008A78", "#B8820C", "#C2527C", "#5F8A2E")
DEFAULT_FONTS = {
    "display": "Instrument Serif",
    "body": "Source Serif 4",
    "ui": "Libre Franklin",
    "hand": "Caveat",
    "mono": "IBM Plex Mono",
}
# The default families, so a page renders even when no font list is supplied.
BUILTIN_FONTS = {
    "Instrument Serif": {"axes": "ital@0;1", "roles": ["display"], "kind": "serif"},
    "Source Serif 4": {
        "axes": "ital,opsz,wght@0,8..60,400;0,8..60,600;1,8..60,400",
        "roles": ["body"],
        "kind": "serif",
    },
    "Libre Franklin": {
        "axes": "ital,wght@0,400;0,500;0,600;0,700;1,400",
        "roles": ["ui"],
        "kind": "sans",
    },
    "Caveat": {"axes": "wght@400;600", "roles": ["hand"], "kind": "hand"},
    "IBM Plex Mono": {
        "axes": "ital,wght@0,400;0,500;0,600;1,400",
        "roles": ["mono"],
        "kind": "mono",
    },
}
FALLBACKS = {
    "serif": '"Iowan Old Style", "Palatino Linotype", Georgia, serif',
    "sans": '"Helvetica Neue", Arial, sans-serif',
    "hand": '"Segoe Print", "Bradley Hand", cursive',
    "mono": 'ui-monospace, "SF Mono", Menlo, monospace',
}
PROGRESS = ("arches", "track", "tape", "flags", "clock", "steps")
ICONS = (
    "parcel",
    "van",
    "truck",
    "cart",
    "plane",
    "train",
    "ship",
    "pin",
    "ball",
    "boot",
    "rocket",
    "dot",
)
TRACK_LINES = ("solid", "dashed", "belt", "road", "rail")
MARKS = ("arch", "label", "tag", "sign", "badge", "flag", "plain", "step", "none")
NUMBERING = ("roman", "decimal", "padded", "alpha")
STAT_STYLES = ("rule", "receipt", "cards", "ticket")
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_NAME = re.compile(r"^[a-z][a-z0-9-]{0,24}$")
ROMAN = ("I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X", "XI", "XII", "XIII", "XIV")


class ThemeError(ValueError):
    """A theme that cannot be used, with what to change."""


@dataclass
class Theme:
    """Everything the renderer and runtime need from a theme."""

    css: str
    fonts_url: str
    progress: dict[str, Any]
    mark: dict[str, str]
    stats: str
    warnings: list[str] = field(default_factory=list)

    def number(self, index: int) -> str:
        """The chapter number as the theme writes it: IV, 4, 04 or D."""
        style = self.mark.get("format", "roman")
        if style == "decimal":
            return str(index + 1)
        if style == "padded":
            return f"{index + 1:02d}"
        if style == "alpha":
            return chr(ord("A") + index % 26)
        return ROMAN[index % len(ROMAN)]


# ------------------------------------------------------------------ color math
def hex_rgb(value: str) -> RGB:
    if not _HEX.match(value):
        raise ThemeError(f"color {value!r} must be written #rrggbb")
    return (int(value[1:3], 16) / 255, int(value[3:5], 16) / 255, int(value[5:7], 16) / 255)


def rgb_hex(rgb: RGB) -> str:
    return "#" + "".join(f"{round(min(max(c, 0.0), 1.0) * 255):02X}" for c in rgb)


def luminance(rgb: RGB) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (lin(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio between two #rrggbb colors."""
    la, lb = luminance(hex_rgb(a)), luminance(hex_rgb(b))
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def mix(a: str, b: str, t: float) -> str:
    """Blend from a (t=0) to b (t=1)."""
    ra, rb = hex_rgb(a), hex_rgb(b)
    return rgb_hex(
        (ra[0] + (rb[0] - ra[0]) * t, ra[1] + (rb[1] - ra[1]) * t, ra[2] + (rb[2] - ra[2]) * t)
    )


def reach(color: str, background: str, target: float, toward: str) -> str:
    """Move `color` toward `toward` in small steps until it reaches `target` contrast."""
    out = color
    for step in range(1, 41):
        if contrast(out, background) >= target:
            return out
        out = mix(color, toward, step / 40)
    return out


def rgba(color: str, alpha: float) -> str:
    r, g, b = (round(c * 255) for c in hex_rgb(color))
    return f"rgba({r}, {g}, {b}, {alpha:.2f})"


# ---------------------------------------------------------------------- build
def build(
    spec: Mapping[str, Any] | None, fonts: Mapping[str, Any], needs: frozenset[str] = frozenset()
) -> Theme:
    """Turn a story's theme (or none) into CSS, a font URL and runtime settings.

    `needs` names the optional font roles the page uses (hand, mono); they load only then.
    """
    spec = dict(spec or {})
    warnings: list[str] = []
    known = {"palette", "dark", "fonts", "progress", "chapter_mark", "stats"}
    for key in sorted(set(spec) - known):
        warnings.append(f"theme.{key} is not used; theme takes {', '.join(sorted(known))}")
    palette = dict(spec.get("palette", {}))
    colors = _colors(palette, warnings)
    dark_spec = dict(spec.get("dark", {}))
    progress = _progress(dict(spec.get("progress", {})))
    mark = _mark(spec.get("chapter_mark", {}))
    stats = str(spec.get("stats", "rule"))
    if stats not in STAT_STYLES:
        raise ThemeError(f"theme.stats {stats!r} must be one of {', '.join(STAT_STYLES)}")
    if stats in ("receipt", "ticket"):
        needs = needs | {"mono"}
    font_css, url = _fonts(dict(spec.get("fonts", {})), fonts, needs)
    light = _light_tokens(colors)
    dark = _dark_tokens(colors, dark_spec, warnings)
    css = _css(light, dark, font_css, colors)
    return Theme(css, url, progress, mark, stats, warnings)


def _colors(palette: Mapping[str, Any], warnings: list[str]) -> dict[str, Any]:
    allowed = {"paper", "ink", "accent", "legacy", "good", "warn", "bad", "series", "colors"}
    for key in sorted(set(palette) - allowed):
        raise ThemeError(f"theme.palette.{key} is unknown; use {', '.join(sorted(allowed))}")
    out: dict[str, Any] = {k: str(palette.get(k, v)).upper() for k, v in LIGHT.items()}
    for key in LIGHT:
        hex_rgb(out[key])
    if contrast(out["ink"], out["paper"]) < 7:
        raise ThemeError(
            f"ink {out['ink']} on paper {out['paper']} has contrast "
            f"{contrast(out['ink'], out['paper']):.1f}; body text needs at least 7"
        )
    if luminance(hex_rgb(out["paper"])) < 0.6:
        raise ThemeError("theme.palette.paper must be a light color; dark mode is derived")
    series = [str(s).upper() for s in palette.get("series", [])]
    for s in series:
        hex_rgb(s)
    base = [out["accent"], out["legacy"], *SERIES[2:]]
    out["series"] = (series + base[len(series) :])[:6] if series else base
    extra: dict[str, str] = {}
    for name, value in dict(palette.get("colors", {})).items():
        if not _NAME.match(str(name)):
            raise ThemeError(f"theme color name {name!r} must be lowercase letters, digits, -")
        extra[str(name)] = str(value).upper()
        hex_rgb(extra[str(name)])
    out["colors"] = extra
    for i, s in enumerate(out["series"]):
        if contrast(s, out["paper"]) < 3:
            warnings.append(f"series color s{i + 1} {s} is faint on paper (contrast below 3)")
    return out


def _light_tokens(c: Mapping[str, Any]) -> dict[str, str]:
    paper, ink, accent = c["paper"], c["ink"], c["accent"]
    muted = reach(mix(ink, paper, 0.45), paper, 4.6, ink)
    t = {
        "paper": paper,
        "print": mix(paper, "#FFFFFF", 0.35),
        "surface": mix(paper, ink, 0.04),
        "surface-2": mix(paper, "#FFFFFF", 0.7),
        "ink": ink,
        "ink-2": reach(mix(ink, paper, 0.25), paper, 7, ink),
        "muted": muted,
        "rule": mix(paper, ink, 0.15),
        "rule-2": mix(paper, ink, 0.08),
        "grid": mix(paper, ink, 0.1),
        "accent": accent,
        "accent-text": reach(accent, paper, 4.6, ink),
        "accent-wash": rgba(accent, 0.1),
        "legacy": c["legacy"],
        "legacy-text": reach(c["legacy"], paper, 4.6, ink),
        "good": reach(c["good"], paper, 4.6, ink),
        "warn": reach(c["warn"], paper, 4.6, ink),
        "bad": reach(c["bad"], paper, 4.6, ink),
        "good-wash": rgba(c["good"], 0.12),
        "bad-wash": rgba(c["bad"], 0.12),
        "tip-bg": ink,
        "tip-ink": paper,
        "on-accent": "#FFFFFF" if contrast("#FFFFFF", accent) >= 3.5 else ink,
    }
    for i, s in enumerate(c["series"]):
        t[f"s{i + 1}"] = s
    for k, step in enumerate((0.08, 0.22, 0.42, 0.66, 1.0)):
        t[f"seq-{k}"] = mix(paper, accent, step)
    t["seq-5"] = mix(accent, ink, 0.4)
    for name, value in c["colors"].items():
        t[f"c-{name}"] = value
    return t


def _dark_tokens(
    c: Mapping[str, Any], spec: Mapping[str, Any], warnings: list[str]
) -> dict[str, str]:
    for key in sorted(set(spec) - {"paper", "ink", "accent", "legacy"}):
        raise ThemeError(f"theme.dark.{key} is unknown; use paper, ink, accent, legacy")
    hue = c["paper"]
    paper = str(spec.get("paper", mix(DARK["paper"], hue, 0.04))).upper()
    ink = str(spec.get("ink", mix(DARK["ink"], hue, 0.3))).upper()
    hex_rgb(paper)
    hex_rgb(ink)
    if contrast(ink, paper) < 7:
        raise ThemeError(f"dark ink {ink} on dark paper {paper} needs contrast of at least 7")

    def lift(color: str, target: float) -> str:
        return reach(color, paper, target, "#FFFFFF")

    accent = str(spec.get("accent", lift(c["accent"], 4.6))).upper()
    legacy = str(spec.get("legacy", lift(c["legacy"], 4.6))).upper()
    t = {
        "paper": paper,
        "print": mix(c["paper"], "#FFFFFF", 0.35),
        "surface": mix(paper, ink, 0.05),
        "surface-2": mix(paper, ink, 0.08),
        "ink": ink,
        "ink-2": mix(ink, paper, 0.2),
        "muted": reach(mix(ink, paper, 0.42), paper, 4.6, ink),
        "rule": mix(paper, ink, 0.16),
        "rule-2": mix(paper, ink, 0.08),
        "grid": mix(paper, ink, 0.11),
        "accent": accent,
        "accent-text": lift(accent, 6),
        "accent-wash": rgba(accent, 0.16),
        "legacy": legacy,
        "legacy-text": lift(legacy, 6),
        "good": lift(c["good"], 4.6),
        "warn": lift(c["warn"], 4.6),
        "bad": lift(c["bad"], 4.6),
        "good-wash": rgba(lift(c["good"], 4.6), 0.16),
        "bad-wash": rgba(lift(c["bad"], 4.6), 0.16),
        "tip-bg": ink,
        "tip-ink": paper,
        "on-accent": paper if contrast(paper, accent) >= 3.5 else "#FFFFFF",
    }
    for i, s in enumerate(c["series"]):
        t[f"s{i + 1}"] = lift(s, 3.2)
    for k, step in enumerate((0.1, 0.24, 0.42, 0.64, 1.0)):
        t[f"seq-{k}"] = mix(paper, accent, step)
    t["seq-5"] = mix(accent, "#FFFFFF", 0.45)
    for name, value in c["colors"].items():
        t[f"c-{name}"] = lift(value, 3.0)
    if contrast(accent, paper) < 3:
        warnings.append(f"dark accent {accent} is faint on {paper}")
    return t


def _fonts(
    spec: Mapping[str, Any], table: Mapping[str, Any], needs: frozenset[str]
) -> tuple[str, str]:
    roles = dict(DEFAULT_FONTS)
    for role, family in spec.items():
        if role not in roles:
            raise ThemeError(f"theme.fonts.{role} is unknown; roles are {', '.join(roles)}")
        roles[role] = str(family)
    css = ""
    families: dict[str, str] = {}
    table = {**BUILTIN_FONTS, **table}
    for role, family in roles.items():
        entry = table.get(family)
        if not isinstance(entry, Mapping):
            options = ", ".join(sorted(n for n, e in table.items() if role in e.get("roles", ())))
            raise ThemeError(
                f"font {family!r} for {role} is not in the font list; use one of: {options}"
            )
        fallback = FALLBACKS[str(entry.get("kind", "sans"))]
        css += f'  --f-{role}: "{family}", {fallback};\n'
        if role in ("display", "body", "ui") or role in spec or role in needs:
            families[family] = str(entry.get("axes", ""))
    parts = []
    for family, axes in families.items():
        name = family.replace(" ", "+")
        parts.append(f"family={name}:{axes}" if axes else f"family={name}")
    url = "https://fonts.googleapis.com/css2?" + "&".join(parts) + "&display=swap"
    return css, url


def _progress(spec: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(spec.get("kind", "arches"))
    if kind not in PROGRESS:
        raise ThemeError(f"theme.progress.kind {kind!r} must be one of {', '.join(PROGRESS)}")
    out: dict[str, Any] = {"kind": kind}
    icon = str(spec.get("icon", "dot"))
    if icon not in ICONS:
        raise ThemeError(f"theme.progress.icon {icon!r} must be one of {', '.join(ICONS)}")
    line = str(spec.get("line", "solid"))
    if line not in TRACK_LINES:
        raise ThemeError(f"theme.progress.line {line!r} must be one of {', '.join(TRACK_LINES)}")
    out.update(icon=icon, line=line)
    if "total" in spec:
        out["total"] = float(spec["total"])
    for key in ("unit", "label", "start_label", "end_label"):
        if key in spec:
            out[key] = str(spec[key])
    return out


def _mark(spec: Any) -> dict[str, str]:
    if isinstance(spec, str):
        spec = {"style": spec}
    spec = dict(spec or {})
    style = str(spec.get("style", "arch"))
    if style not in MARKS:
        raise ThemeError(f"theme.chapter_mark.style {style!r} must be one of {', '.join(MARKS)}")
    fmt = str(spec.get("format", "roman" if style == "arch" else "decimal"))
    if fmt not in NUMBERING:
        raise ThemeError(f"theme.chapter_mark.format {fmt!r} must be one of {', '.join(NUMBERING)}")
    return {"style": style, "format": fmt, "prefix": str(spec.get("prefix", ""))}


def _block(tokens: Mapping[str, str]) -> str:
    return "".join(f"  --{k}: {v};\n" for k, v in tokens.items())


def _css(
    light: Mapping[str, str], dark: Mapping[str, str], fonts: str, c: Mapping[str, Any]
) -> str:
    names = ["accent", "legacy", "ink", "muted", "paper", "surface", "good", "bad"]
    names += [f"s{i}" for i in range(1, 7)] + [f"c-{n}" for n in c["colors"]]
    utilities = "".join(
        f".f-{n.removeprefix('c-')} {{ fill: var(--{n}); }} "
        f".s-{n.removeprefix('c-')} {{ stroke: var(--{n}); }} "
        f".t-{n.removeprefix('c-')} {{ color: var(--{n}); }}\n"
        for n in names
    )
    dark_block = (
        _block(dark) + "  --frame-pad: 12px; --frame-shadow: 0 18px 50px rgba(0, 0, 0, .55);\n"
    )
    return (
        "/* Theme: tokens derived by chronicle from the story's palette and fonts. */\n"
        f":root {{\n{_block(light)}{fonts}}}\n"
        "@media (prefers-color-scheme: dark) {\n"
        f'  :root:not([data-theme="light"]) {{\n{dark_block}  color-scheme: dark; }}\n}}\n'
        f':root[data-theme="dark"] {{\n{dark_block}  color-scheme: dark;\n}}\n'
        f"{utilities}"
    )
