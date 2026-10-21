"""How numbers are written everywhere: digest, dashboard and the write-up check agree on these."""

from __future__ import annotations


def decimals_for(value: float) -> int:
    magnitude = abs(value)
    if magnitude >= 100:
        return 0
    if magnitude >= 10:
        return 1
    return 2


def plain(value: float) -> str:
    """1234.5 -> '1,235'; 12.34 -> '12.3'; 0.553 -> '0.55'; trailing zeros dropped."""
    text = f"{value:,.{decimals_for(value)}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def with_unit(value: float | None, unit: str) -> str:
    if value is None:
        return "n/a"
    if unit in ("instructions", "count", "ops", "bytes", "commits", "mutations"):
        return f"{compact(value)} {unit}"
    return f"{plain(value)} {unit}"


def compact(value: float) -> str:
    """Large counts: 1.24 B, 620 M, 45.2 K."""
    magnitude = abs(value)
    for size, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if magnitude >= size:
            return f"{plain(value / size)} {suffix}"
    return plain(value)


def speedup(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{plain(value)}x"


def pct(value: float | None, signed: bool = True) -> str:
    if value is None:
        return "n/a"
    text = plain(abs(value))
    if not signed:
        return f"{text}%"
    sign = "+" if value > 0 else "-" if value < 0 else ""
    return f"{sign}{text}%"


def p_value(value: float | None) -> str:
    if value is None:
        return "n/a"
    return "<0.001" if value < 0.001 else f"{value:.3f}"
