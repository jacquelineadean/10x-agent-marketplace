"""SVG path data and transforms, flattened to point lists.

Standard library only, so the parser can be tested without NumPy. Curves become short
straight segments about `step` units long, which is finer than the painter's wobble.
"""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from dataclasses import dataclass

Point = tuple[float, float]
Matrix = tuple[float, float, float, float, float, float]
IDENTITY: Matrix = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

_NUMBER = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
_TRANSFORM = re.compile(r"(matrix|translate|scale|rotate|skewX|skewY)\s*\(([^)]*)\)")


class PathError(ValueError):
    """Path data or a transform that cannot be read."""


@dataclass
class Subpath:
    """One continuous run of a path; `closed` when it ended with Z."""

    points: list[Point]
    closed: bool


# ---------------------------------------------------------------- transforms
def multiply(m: Matrix, n: Matrix) -> Matrix:
    """The transform that applies `n` first, then `m` (SVG nesting order)."""
    a, b, c, d, e, f = m
    a2, b2, c2, d2, e2, f2 = n
    return (
        a * a2 + c * b2,
        b * a2 + d * b2,
        a * c2 + c * d2,
        b * c2 + d * d2,
        a * e2 + c * f2 + e,
        b * e2 + d * f2 + f,
    )


def apply(m: Matrix, point: Point) -> Point:
    a, b, c, d, e, f = m
    x, y = point
    return (a * x + c * y + e, b * x + d * y + f)


def scale_of(m: Matrix) -> float:
    """Average linear scale of a transform, for stroke widths and curve steps."""
    return math.sqrt(abs(m[0] * m[3] - m[1] * m[2])) or 1.0


def parse_transform(text: str | None) -> Matrix:
    """Read an SVG transform list such as `translate(10 20) rotate(-8 50 50)`."""
    m = IDENTITY
    if not text:
        return m
    consumed = 0
    for match in _TRANSFORM.finditer(text):
        if text[consumed : match.start()].strip(" ,\t\n"):
            raise PathError(f"cannot read transform {text!r}")
        consumed = match.end()
        name = match.group(1)
        args = [float(v) for v in _NUMBER.findall(match.group(2))]
        m = multiply(m, _one_transform(name, args, text))
    if text[consumed:].strip(" ,\t\n"):
        raise PathError(f"cannot read transform {text!r}")
    return m


def _one_transform(name: str, args: list[float], text: str) -> Matrix:
    if name == "matrix" and len(args) == 6:
        return (args[0], args[1], args[2], args[3], args[4], args[5])
    if name == "translate" and len(args) in (1, 2):
        return (1.0, 0.0, 0.0, 1.0, args[0], args[1] if len(args) == 2 else 0.0)
    if name == "scale" and len(args) in (1, 2):
        return (args[0], 0.0, 0.0, args[1] if len(args) == 2 else args[0], 0.0, 0.0)
    if name == "rotate" and len(args) in (1, 3):
        rad = math.radians(args[0])
        cos, sin = math.cos(rad), math.sin(rad)
        turn: Matrix = (cos, sin, -sin, cos, 0.0, 0.0)
        if len(args) == 3:
            cx, cy = args[1], args[2]
            turn = multiply(multiply((1.0, 0.0, 0.0, 1.0, cx, cy), turn), (1, 0, 0, 1, -cx, -cy))
        return turn
    if name == "skewX" and len(args) == 1:
        return (1.0, 0.0, math.tan(math.radians(args[0])), 1.0, 0.0, 0.0)
    if name == "skewY" and len(args) == 1:
        return (1.0, math.tan(math.radians(args[0])), 0.0, 1.0, 0.0, 0.0)
    raise PathError(f"bad arguments for {name} in transform {text!r}")


# ---------------------------------------------------------------- path data
class _Reader:
    """Walks path data one number or flag at a time; arc flags may be written unspaced."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def _skip(self) -> None:
        while self.pos < len(self.text) and self.text[self.pos] in " \t\r\n,":
            self.pos += 1

    def command(self) -> str | None:
        self._skip()
        if self.pos < len(self.text) and self.text[self.pos].isalpha():
            self.pos += 1
            return self.text[self.pos - 1]
        return None

    def has_number(self) -> bool:
        self._skip()
        return self.pos < len(self.text) and self.text[self.pos] in "+-.0123456789"

    def number(self) -> float:
        self._skip()
        match = _NUMBER.match(self.text, self.pos)
        if not match:
            raise PathError(f"expected a number at {self.text[self.pos : self.pos + 12]!r}")
        self.pos = match.end()
        return float(match.group(0))

    def flag(self) -> bool:
        self._skip()
        if self.pos < len(self.text) and self.text[self.pos] in "01":
            self.pos += 1
            return self.text[self.pos - 1] == "1"
        raise PathError(f"expected an arc flag at {self.text[self.pos : self.pos + 12]!r}")

    def done(self) -> bool:
        self._skip()
        return self.pos >= len(self.text)


ARGS = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7, "Z": 0}


def parse_path(d: str, step: float = 3.0) -> list[Subpath]:
    """Flatten path data to subpaths of points; curves are split into ~`step` long pieces."""
    reader = _Reader(d)
    subpaths: list[Subpath] = []
    current: list[Point] = []
    pen: Point = (0.0, 0.0)
    start: Point = (0.0, 0.0)
    last_ctrl: Point | None = None
    last_cmd = ""
    cmd = reader.command()
    if cmd is None and not reader.done():
        raise PathError(f"path data must start with a command: {d[:20]!r}")
    while cmd is not None:
        upper = cmd.upper()
        if upper not in ARGS:
            raise PathError(f"unknown path command {cmd!r}")
        rel = cmd.islower()
        if upper == "Z":
            if current:
                subpaths.append(Subpath(current, True))
            current, pen, last_ctrl, last_cmd = [], start, None, "Z"
            cmd = reader.command()
            continue
        while True:
            ox, oy = pen if rel else (0.0, 0.0)
            if upper == "M":
                if current:
                    subpaths.append(Subpath(current, False))
                pen = start = (reader.number() + ox, reader.number() + oy)
                current = [pen]
                last_ctrl = None
                upper = "L"  # further pairs after a moveto are linetos
            elif upper in ("L", "H", "V"):
                if upper == "L":
                    pen = (reader.number() + ox, reader.number() + oy)
                elif upper == "H":
                    pen = (reader.number() + ox, pen[1])
                else:
                    pen = (pen[0], reader.number() + oy)
                current = current or [start]
                current.append(pen)
                last_ctrl = None
            elif upper in ("C", "S"):
                if upper == "C":
                    c1 = (reader.number() + ox, reader.number() + oy)
                else:
                    c1 = _reflect(pen, last_ctrl) if last_cmd in ("C", "S") else pen
                c2 = (reader.number() + ox, reader.number() + oy)
                end = (reader.number() + ox, reader.number() + oy)
                current = current or [pen]
                current.extend(_cubic(pen, c1, c2, end, step))
                last_ctrl, pen = c2, end
            elif upper in ("Q", "T"):
                if upper == "Q":
                    c = (reader.number() + ox, reader.number() + oy)
                else:
                    c = _reflect(pen, last_ctrl) if last_cmd in ("Q", "T") else pen
                end = (reader.number() + ox, reader.number() + oy)
                current = current or [pen]
                current.extend(_quadratic(pen, c, end, step))
                last_ctrl, pen = c, end
            else:
                rx, ry, rot = reader.number(), reader.number(), reader.number()
                large, sweep = reader.flag(), reader.flag()
                end = (reader.number() + ox, reader.number() + oy)
                current = current or [pen]
                current.extend(_arc(pen, rx, ry, rot, large, sweep, end, step))
                pen, last_ctrl = end, None
            last_cmd = upper
            if not reader.has_number():
                break
        cmd = reader.command()
        if cmd is None and not reader.done():
            raise PathError(
                f"unexpected text in path data near {d[reader.pos : reader.pos + 12]!r}"
            )
    if current:
        subpaths.append(Subpath(current, False))
    return [s for s in subpaths if len(s.points) >= 2]


def _reflect(pen: Point, ctrl: Point | None) -> Point:
    if ctrl is None:
        return pen
    return (2 * pen[0] - ctrl[0], 2 * pen[1] - ctrl[1])


def _count(length: float, step: float) -> int:
    return max(2, min(96, int(math.ceil(length / max(step, 0.25)))))


def _cubic(p0: Point, p1: Point, p2: Point, p3: Point, step: float) -> list[Point]:
    length = math.dist(p0, p1) + math.dist(p1, p2) + math.dist(p2, p3)
    n = _count(length, step)
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append(
            (
                u**3 * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t**3 * p3[0],
                u**3 * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t**3 * p3[1],
            )
        )
    return out


def _quadratic(p0: Point, p1: Point, p2: Point, step: float) -> list[Point]:
    n = _count(math.dist(p0, p1) + math.dist(p1, p2), step)
    out = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        out.append(
            (
                u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
            )
        )
    return out


def _arc(
    p0: Point,
    rx: float,
    ry: float,
    rotation: float,
    large: bool,
    sweep: bool,
    p1: Point,
    step: float,
) -> list[Point]:
    """Endpoint arc to points, following SVG 1.1 appendix F.6."""
    if p0 == p1:
        return []
    rx, ry = abs(rx), abs(ry)
    if rx < 1e-9 or ry < 1e-9:
        return [p1]
    phi = math.radians(rotation)
    cos, sin = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1p, y1p = cos * dx + sin * dy, -sin * dx + cos * dy
    lam = (x1p / rx) ** 2 + (y1p / ry) ** 2
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1p * y1p - ry * ry * x1p * x1p
    den = rx * rx * y1p * y1p + ry * ry * x1p * x1p
    coef = math.sqrt(max(num / den, 0.0)) if den else 0.0
    if large == sweep:
        coef = -coef
    cxp, cyp = coef * rx * y1p / ry, -coef * ry * x1p / rx
    cx = cos * cxp - sin * cyp + (p0[0] + p1[0]) / 2
    cy = sin * cxp + cos * cyp + (p0[1] + p1[1]) / 2
    theta1 = math.atan2((y1p - cyp) / ry, (x1p - cxp) / rx)
    theta2 = math.atan2((-y1p - cyp) / ry, (-x1p - cxp) / rx)
    delta = theta2 - theta1
    if sweep and delta < 0:
        delta += 2 * math.pi
    elif not sweep and delta > 0:
        delta -= 2 * math.pi
    n = _count(abs(delta) * max(rx, ry), step)
    out = []
    for i in range(1, n + 1):
        t = theta1 + delta * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        out.append((cos * x - sin * y + cx, sin * x + cos * y + cy))
    out[-1] = p1
    return out


# ------------------------------------------------------------ basic shapes
def numbers(text: str | None) -> list[float]:
    return [float(v) for v in _NUMBER.findall(text or "")]


def ellipse_points(cx: float, cy: float, rx: float, ry: float, step: float) -> list[Point]:
    n = max(12, min(180, int(2 * math.pi * max(rx, ry) / max(step, 0.5))))
    return [
        (cx + rx * math.cos(2 * math.pi * i / n), cy + ry * math.sin(2 * math.pi * i / n))
        for i in range(n)
    ]


def rect_points(
    x: float, y: float, w: float, h: float, rx: float, ry: float, step: float
) -> list[Point]:
    """A rectangle outline, with rounded corners when rx or ry is set."""
    rx, ry = min(rx, w / 2), min(ry, h / 2)
    if rx <= 0 or ry <= 0:
        return [(x, y), (x + w, y), (x + w, y + h), (x, y + h)]
    out: list[Point] = []
    corners = [
        (x + w - rx, y + ry, -90),
        (x + w - rx, y + h - ry, 0),
        (x + rx, y + h - ry, 90),
        (x + rx, y + ry, 180),
    ]
    n = max(3, int(math.pi / 2 * max(rx, ry) / max(step, 0.5)))
    for cx, cy, a0 in corners:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            out.append((cx + rx * math.cos(a), cy + ry * math.sin(a)))
    return out


def transform_points(m: Matrix, points: Sequence[Point]) -> list[Point]:
    return [apply(m, p) for p in points]
