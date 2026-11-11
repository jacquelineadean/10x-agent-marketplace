"""The upload manifest for `--to google` and `--to microsoft`: what Claude uploads, and the
question the user answers before it does.

Code never uploads. Claude sends the file through the user's Google Drive or Microsoft
365 connector, and only after the user says yes to `confirm` (constitution amendment 1).
The deck goes as the .pptx that claude.ai's Slides type downloads, or as the PDF that
`briefing slides --pdf` prints.
"""

from __future__ import annotations

import hashlib
import io
import re
import zipfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

SERVICES = {"google": "Google Drive", "microsoft": "Microsoft 365 (OneDrive or SharePoint)"}
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
PDF = "application/pdf"
GOOGLE_SLIDES = "application/vnd.google-apps.presentation"
SLIDE_PART = re.compile(r"^ppt/slides/slide\d+\.xml$")
PDF_PAGE = re.compile(rb"/Type\s*/Page(?!s)")


class UploadError(ValueError):
    """A file that is not a deck Claude can upload, with what to pass instead."""


def _slides(data: bytes, kind: str) -> int:
    if kind == PDF:
        if not data.startswith(b"%PDF-"):
            raise UploadError("the .pdf file is not a PDF")
        return len(PDF_PAGE.findall(data))
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as deck:
            names = deck.namelist()
    except zipfile.BadZipFile as exc:
        raise UploadError("the .pptx file is not a PowerPoint file") from exc
    if "ppt/presentation.xml" not in names:
        raise UploadError("the .pptx file has no presentation in it")
    return sum(1 for n in names if SLIDE_PART.match(n))


def _size(count: int) -> str:
    return f"{count / 1_048_576:.1f} MB" if count >= 1_048_576 else f"{max(1, count // 1024)} KB"


def manifest(service: str, path: Path, data: bytes, story: Mapping[str, Any]) -> dict[str, Any]:
    """The manifest for one upload of the deck at `path` to `service`."""
    kind = {".pptx": PPTX, ".pdf": PDF}.get(path.suffix.lower())
    if kind is None:
        raise UploadError("--file must be the deck's .pptx or .pdf")
    slides = _slides(data, kind)
    title = str(story.get("meta", {}).get("title", "Deck")).strip() or "Deck"
    name = re.sub(r"[\\/:*?\"<>|]+", "-", title)[:120] + path.suffix.lower()
    labels = [
        str(s.get("label") or s.get("id"))
        for s in story.get("sources", [])
        if isinstance(s, Mapping) and (s.get("label") or s.get("id"))
    ]
    shows = ", ".join(labels[:-1]) + f" and {labels[-1]}" if len(labels) > 1 else "".join(labels)
    where = SERVICES[service]
    convert = " as Google Slides" if service == "google" and kind == PPTX else ""
    confirm = f'Upload "{name}" ({slides} slides, {_size(len(data))}) to {where}{convert}?'
    if shows:
        confirm += f" It shows numbers from {shows}."
    out: dict[str, Any] = {
        "destination": service,
        "service": where,
        "file": str(path),
        "name": name,
        "mime_type": kind,
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "slides": slides,
        "sources": labels,
        "confirm": confirm,
    }
    if convert:
        out["convert_to"] = GOOGLE_SLIDES
    return out
