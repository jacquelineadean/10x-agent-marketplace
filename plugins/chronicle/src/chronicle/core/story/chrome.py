"""Page chrome drawn from a subject's world: progress devices, marks, stat skins, frames.

The engine offers neutral chrome: a step bar, label and plain marks, ruled stats and cards.
These entries join it in the order theme errors list the choices, and make the arches
device and the arch mark the defaults, so a page with no theme looks as it always has.
"""

from __future__ import annotations

from chronicle_engine import registry

# Progress devices, and whether each needs a drawn path.
PROGRESS = {
    "arches": False,
    "track": False,
    "route": True,
    "tape": False,
    "flags": False,
    "clock": False,
}
LINES = ("belt", "road", "rail")
# A printed slip beside the hero's title, set in the mono face.
SLIP = registry.StatSkin(paper=True, fonts=frozenset({"mono"}))
MAT = (
    ".plate .frame { --frame-pad: clamp(8px, 1.6vw, 16px); background: var(--surface-2); "
    "--frame-shadow: 0 1px 2px rgba(0, 0, 0, .08), 0 14px 32px -18px rgba(0, 0, 0, .4); }\n"
)
TAPE = (
    ".plate .frame { position: relative; }\n"
    '.plate .frame::before, .plate .frame::after { content: ""; position: absolute; '
    "z-index: 3; top: 0; width: 5.5rem; height: 1.35rem; pointer-events: none; "
    "background: color-mix(in srgb, var(--accent) 24%, transparent); }\n"
    ".plate .frame::before { left: 1.4rem; transform: rotate(-4deg); }\n"
    ".plate .frame::after { right: 1.4rem; transform: rotate(5deg); }\n"
)
# The stylesheet and script the chrome above draws with, on every chronicle page.
PARTS = ("css/13-arch-mark.css", "css/21-identity-devices.css", "js/41-devices.js")


def register() -> None:
    """Add chronicle's chrome to the engine's and make it the default."""
    chrome = registry.CHROME
    registry.insert(chrome.progress, PROGRESS, before="steps")
    chrome.lines[:] = list(dict.fromkeys([*chrome.lines, *LINES]))
    registry.insert(chrome.marks, {"arch": "roman"}, before="label")
    registry.insert(
        chrome.marks, dict.fromkeys(("tag", "sign", "badge", "flag"), "decimal"), before="plain"
    )
    registry.insert(chrome.stats, {"receipt": SLIP}, before="cards")
    registry.insert(chrome.stats, {"ticket": SLIP})
    registry.insert(chrome.frames, {"mat": MAT, "tape": TAPE})
    chrome.progress_default = "arches"
    chrome.mark_default = "arch"
    registry.add_parts(always=PARTS)
