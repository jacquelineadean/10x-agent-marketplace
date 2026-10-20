"""An animated GIF encoder in NumPy, written for flat figures with a few exact colors.

One palette serves every frame. The most frequent colors of the sample frames (paper,
ink, the accent) keep their exact values, so flat areas never shimmer; median cut picks
the rest. Each frame after the first stores only the box of pixels that changed, with
unchanged pixels transparent, and frames that change nothing lengthen the frame before.
"""

from __future__ import annotations

import struct
from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

Image = npt.NDArray[np.uint8]
COLORS = 255  # palette entries for pixels; index 255 marks an unchanged pixel
CLEAR = 255
EXACT = 48  # frequent colors kept exactly
LEVELS = 64  # lookup table steps per channel


def palette(samples: Sequence[Image]) -> Image:
    """A 255-color palette (RGB rows) for frames that look like the samples (BGR)."""
    pixels = np.concatenate([s.reshape(-1, 3)[:, ::-1] for s in samples])
    if len(pixels) > 600_000:
        pixels = pixels[:: len(pixels) // 600_000 + 1]
    keys = (
        (pixels[:, 0].astype(np.int64) << 16) | (pixels[:, 1].astype(np.int64) << 8) | pixels[:, 2]
    )
    values, counts = np.unique(keys, return_counts=True)
    order = np.argsort(-counts)
    exact_keys = values[order[:EXACT]]
    share = int(counts[order[:EXACT]].sum()) / max(1, int(counts.sum()))
    exact = np.stack([(exact_keys >> 16) & 255, (exact_keys >> 8) & 255, exact_keys & 255], 1)
    rest = pixels[~np.isin(keys, exact_keys)]
    room = COLORS - len(exact)
    cut = _median_cut(rest, room) if len(rest) and share < 0.999 else np.zeros((0, 3), np.int64)
    table = np.concatenate([exact, cut]).astype(np.uint8)
    if len(table) < COLORS:
        table = np.concatenate([table, np.zeros((COLORS - len(table), 3), np.uint8)])
    return table[:COLORS]


def _median_cut(pixels: npt.NDArray[np.uint8], count: int) -> npt.NDArray[np.int64]:
    boxes = [pixels.astype(np.int64)]
    while len(boxes) < count:
        spans = [(b.max(0) - b.min(0)).max() if len(b) > 1 else -1 for b in boxes]
        widest = int(np.argmax(spans))
        if spans[widest] <= 0:
            break
        box = boxes.pop(widest)
        axis = int(np.argmax(box.max(0) - box.min(0)))
        box = box[np.argsort(box[:, axis], kind="stable")]
        half = len(box) // 2
        boxes += [box[:half], box[half:]]
    return np.array([b.mean(0).round() for b in boxes if len(b)], np.int64).reshape(-1, 3)


class Writer:
    """Frames in, GIF bytes out; holds one frame back to merge frames that do not change."""

    def __init__(self, width: int, height: int, colors: Image, loop: bool) -> None:
        self.width = width
        self.height = height
        self.colors = colors
        self.lookup = _lookup(colors)
        self.out = bytearray(b"GIF89a")
        self.out += struct.pack("<HHBBB", width, height, 0xF7, 0, 0)
        table = np.zeros((256, 3), np.uint8)
        table[:COLORS] = colors
        self.out += table.tobytes()
        if loop:
            self.out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"
        self.shown: npt.NDArray[np.uint8] | None = None
        self.pending: tuple[npt.NDArray[np.uint8], tuple[int, int, int, int]] | None = None
        self.pending_cs = 0
        self.clock = 0.0
        self.written_cs = 0

    def add(self, frame: Image, seconds: float) -> None:
        """Add a BGR frame shown for `seconds`."""
        if frame.shape[:2] != (self.height, self.width):
            raise ValueError(
                f"frame is {frame.shape[1]}x{frame.shape[0]}, not {self.width}x{self.height}"
            )
        q = frame.astype(np.int32) * LEVELS // 256
        index = self.lookup[q[..., 2], q[..., 1], q[..., 0]]
        # Delays add up by whole centiseconds of the clock, so rounding never drifts.
        self.clock += seconds
        due = round(self.clock * 100) - self.written_cs
        if self.shown is None:
            self._flush()
            self.pending = (index, (0, 0, self.width, self.height))
        else:
            changed = index != self.shown
            if not changed.any():
                self.pending_cs += due
                self.written_cs += due
                return
            self._flush()
            rows = np.flatnonzero(changed.any(1))
            cols = np.flatnonzero(changed.any(0))
            y0, y1, x0, x1 = rows[0], rows[-1] + 1, cols[0], cols[-1] + 1
            part = index[y0:y1, x0:x1].copy()
            part[~changed[y0:y1, x0:x1]] = CLEAR
            self.pending = (part, (int(x0), int(y0), int(x1 - x0), int(y1 - y0)))
        self.shown = index
        self.pending_cs = due
        self.written_cs += due

    def finish(self) -> bytes:
        self._flush()
        return bytes(self.out) + b"\x3b"

    def _flush(self) -> None:
        if self.pending is None:
            return
        pixels, (x, y, w, h) = self.pending
        delay = max(2, self.pending_cs)
        self.out += struct.pack("<BBBBHBB", 0x21, 0xF9, 4, 0x05, delay, CLEAR, 0)
        self.out += struct.pack("<BHHHHB", 0x2C, x, y, w, h, 0)
        self.out += bytes([8]) + _blocks(_lzw(pixels.ravel().tobytes()))
        self.pending = None


def _lookup(colors: Image) -> npt.NDArray[np.uint8]:
    """Nearest palette index for every color on a 64-step grid, as [r, g, b]."""
    steps = (np.arange(LEVELS) * 256 // LEVELS + 256 // LEVELS // 2).astype(np.int32)
    grid = np.stack(np.meshgrid(steps, steps, steps, indexing="ij"), -1).reshape(-1, 3)
    table = colors.astype(np.int32)
    out = np.empty(len(grid), np.uint8)
    for i in range(0, len(grid), 8192):
        chunk = grid[i : i + 8192]
        distance = ((chunk[:, None, :] - table[None, :, :]) ** 2).sum(-1)
        out[i : i + 8192] = distance.argmin(1)
    # Exact palette colors map to themselves even when the grid cell's center is nearer
    # to another entry, so flat areas keep their color.
    q = table * LEVELS // 256
    flat = out.reshape(LEVELS, LEVELS, LEVELS)
    flat[q[:, 0], q[:, 1], q[:, 2]] = np.arange(len(table), dtype=np.uint8)
    return flat


def _lzw(data: bytes) -> bytes:
    """GIF's variable-width LZW for 8-bit codes, emptying the table when it fills."""
    clear, end = 256, 257
    size = 9
    table: dict[int, int] = {}
    next_code = 258
    bits = 0
    count = 0
    out = bytearray()

    def emit(code: int) -> None:
        nonlocal bits, count
        bits |= code << count
        count += size
        while count >= 8:
            out.append(bits & 255)
            bits >>= 8
            count -= 8

    emit(clear)
    prefix = data[0]
    for byte in data[1:]:
        key = prefix << 8 | byte
        code = table.get(key)
        if code is not None:
            prefix = code
            continue
        emit(prefix)
        if next_code < 4096:
            table[key] = next_code
            next_code += 1
            if next_code > 1 << size and size < 12:
                size += 1
        else:
            emit(clear)
            table.clear()
            next_code = 258
            size = 9
        prefix = byte
    emit(prefix)
    # The decoder adds one more entry on reading that last code, and widens its codes
    # if the table just reached the next power of two.
    if next_code == 1 << size and size < 12:
        size += 1
    emit(end)
    if count:
        out.append(bits & 255)
    return bytes(out)


def _blocks(data: bytes) -> bytes:
    out = bytearray()
    for i in range(0, len(data), 255):
        chunk = data[i : i + 255]
        out += bytes([len(chunk)]) + chunk
    return bytes(out) + b"\x00"
