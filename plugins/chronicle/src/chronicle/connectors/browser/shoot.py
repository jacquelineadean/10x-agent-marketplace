"""Screenshots of a built page, taken by a headless Chromium or Chrome already installed.

The browser runs as a separate program with an argument list, never a shell string, and
reads only the local page file it is given.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

CANDIDATES = (
    "chromium",
    "chromium-browser",
    "google-chrome",
    "google-chrome-stable",
    "chrome",
    "msedge",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Chromium.app/Contents/MacOS/Chromium",
    "/opt/pw-browsers/chromium",
)
# Desktop and phone widths a reader is likely to use; the tall windows take in the hero
# and the first chapters in one image.
SIZES = {"desktop": (1280, 2400), "phone": (390, 2000)}
# Headless Chromium will not open a window narrower than this, so narrower pages are
# shot inside a frame of the wanted width, at the left of a window this wide.
MIN_WINDOW = 500


class BrowserError(RuntimeError):
    """No browser was found, or it wrote no image."""


def find(explicit: str | None = None) -> str:
    """The browser to use: the one named, else the first installed candidate."""
    for name in (explicit,) if explicit else CANDIDATES:
        found = shutil.which(name) or (name if Path(name).is_file() else None)
        if found:
            return found
    raise BrowserError(
        "no Chromium or Chrome found; pass --browser PATH, or look at build/index.html yourself"
    )


def shoot(browser: str, page: Path, out: Path, size: tuple[int, int], wait_ms: int) -> Path:
    """Open `page` at `size`, let its scripts and fonts settle for `wait_ms`, save a PNG."""
    out.parent.mkdir(parents=True, exist_ok=True)
    out.unlink(missing_ok=True)
    # "#still" asks the page to skip its arrival animations, so paintings show in color.
    target = page.resolve().as_uri() + "#still"
    width, height = size
    if width < MIN_WINDOW:
        holder = out.with_suffix(".html")
        holder.write_text(
            '<!doctype html><body style="margin:0;background:#888">'
            f'<iframe src="{target}" width="{width}" height="{height}" '
            'style="border:0;display:block;background:#fff"></iframe></body>',
            encoding="utf-8",
        )
        target, width = holder.resolve().as_uri(), MIN_WINDOW
    args = [
        browser,
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--force-device-scale-factor=1",
        "--no-first-run",
        "--disable-background-networking",
        "--disable-component-update",
        f"--window-size={width},{height}",
        f"--virtual-time-budget={wait_ms}",
        f"--screenshot={out}",
    ]
    # Chromium refuses to start its sandbox as root, which is the norm in containers.
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        args.append("--no-sandbox")
    args.append(target)
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=120, check=False)  # noqa: S603  argv list, no shell; the browser path is one found on PATH or named by the user
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BrowserError(f"{browser} did not finish: {exc}") from exc
    if not out.exists():
        tail = (done.stderr or "").strip().splitlines()[-3:]
        raise BrowserError(f"{browser} wrote no screenshot: {' | '.join(tail)}")
    return out
