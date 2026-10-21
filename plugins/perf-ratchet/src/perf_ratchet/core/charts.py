"""Inline SVG charts for the dashboard. Colors come from CSS classes so both themes work."""

from __future__ import annotations

import math
from datetime import date
from html import escape
from typing import Any

from perf_ratchet.core.numbers import compact, plain, speedup

W, H = 360, 150
LEFT, RIGHT, TOP, BOTTOM = 44, 12, 14, 26


def journey_chart(
    journey_id: str, data: dict[str, Any], windows: dict[str, Any], marks: list[dict[str, Any]]
) -> str:
    """Daily values as a line, the target as a dashed rule, windows as bands, ships as ticks."""
    series = [(date.fromisoformat(d), float(v)) for d, v in data.get("series", [])]
    label = f"{data['name']}: daily {data['percentile']} in {data['unit']}"
    if len(series) < 2:
        return _empty(label)
    first, last = series[0][0], series[-1][0]
    span = max((last - first).days, 1)
    values = [v for _, v in series]
    target = data.get("target")
    low = min([*values, target] if target else values)
    high = max([*values, target] if target else values)
    low, high = _nice_range(low, high)

    def x(day: date) -> float:
        return LEFT + (W - LEFT - RIGHT) * (day - first).days / span

    def y(value: float) -> float:
        return TOP + (H - TOP - BOTTOM) * (1 - (value - low) / (high - low))

    parts = [_open(label)]
    for name in ("baseline", "current"):
        window = windows.get(name)
        if window:
            x0 = max(x(date.fromisoformat(window["since"])), LEFT)
            x1 = min(x(date.fromisoformat(window["until"])), W - RIGHT)
            if x1 > x0:
                parts.append(
                    f'<rect class="band band-{name}" x="{x0:.1f}" y="{TOP}" '
                    f'width="{x1 - x0:.1f}" height="{H - TOP - BOTTOM}"/>'
                )
    for tick in _ticks(low, high):
        ty = y(tick)
        parts.append(
            f'<line class="grid" x1="{LEFT}" x2="{W - RIGHT}" y1="{ty:.1f}" y2="{ty:.1f}"/>'
            f'<text class="axis" x="{LEFT - 6}" y="{ty + 3:.1f}" '
            f'text-anchor="end">{compact(tick)}</text>'
        )
    if target:
        ty = y(target)
        parts.append(
            f'<line class="target" x1="{LEFT}" x2="{W - RIGHT}" y1="{ty:.1f}" y2="{ty:.1f}"/>'
            f'<text class="target-label" x="{LEFT + 4}" y="{ty - 4:.1f}">'
            f"target {plain(target)}</text>"
        )
    path = " ".join(
        f"{'M' if i == 0 else 'L'}{x(d):.1f},{y(v):.1f}" for i, (d, v) in enumerate(series)
    )
    area = path + f" L{x(last):.1f},{H - BOTTOM} L{x(first):.1f},{H - BOTTOM} Z"
    parts.append(f'<path class="area" d="{area}"/><path class="line" d="{path}"/>')
    for mark in marks:
        shipped = date.fromisoformat(mark["shipped"])
        if first <= shipped <= last:
            mx = x(shipped)
            parts.append(
                f'<g class="ship"><title>{escape(mark["id"])} {escape(mark["title"])} '
                f"({escape(mark['shipped'])})</title>"
                f'<line x1="{mx:.1f}" x2="{mx:.1f}" y1="{H - BOTTOM}" y2="{H - BOTTOM - 7}"/>'
                f'<circle cx="{mx:.1f}" cy="{H - BOTTOM - 9}" r="2.2"/></g>'
            )
    end_x, end_y = x(last), y(series[-1][1])
    parts.append(
        f'<circle class="end" cx="{end_x:.1f}" cy="{end_y:.1f}" r="3.4"/>'
        f'<text class="axis" x="{LEFT}" y="{H - 8}">{_label(first)}</text>'
        f'<text class="axis" x="{W - RIGHT}" y="{H - 8}" text-anchor="end">{_label(last)}</text>'
        "</svg>"
    )
    return "".join(parts)


def speedup_bars(journeys: dict[str, dict[str, Any]]) -> str:
    """One bar per journey on a log scale from 1x, so 2x and 4x sit at even steps."""
    rows = [(k, v) for k, v in journeys.items() if v.get("speedup")]
    if not rows:
        return _empty("Speedup by journey")
    rows.sort(key=lambda item: -item[1]["speedup"])
    row_h, label_w, width = 26, 170, 640
    height = row_h * len(rows) + 30
    peak = max(max(v["speedup"] for _, v in rows), 2.0)
    lowest = min(min(v["speedup"] for _, v in rows), 1.0)
    log_low, log_high = math.log(lowest), math.log(peak)
    scale = (width - label_w - 70) / max(log_high - log_low, 1e-9)
    zero = label_w + (0 - log_low) * scale
    parts = [
        f'<svg class="chart bars" viewBox="0 0 {width} {height}" role="img" '
        'aria-label="Speedup by journey, log scale">'
    ]
    for index, (journey_id, data) in enumerate(rows):
        y = 8 + index * row_h
        end = label_w + (math.log(data["speedup"]) - log_low) * scale
        x0, x1 = sorted((zero, end))
        state = "good" if data["speedup"] >= 1 else "bad"
        parts.append(
            f'<text class="label" x="{label_w - 10}" y="{y + 15}" text-anchor="end">'
            f"{escape(_short(data['name'], 26))}</text>"
            f'<rect class="bar bar-{state}" x="{x0:.1f}" y="{y + 4}" '
            f'width="{max(x1 - x0, 1.5):.1f}" height="{row_h - 10}">'
            f"<title>{escape(journey_id)}: {speedup(data['speedup'])}</title></rect>"
            f'<text class="value" x="{max(x1, zero) + 6:.1f}" '
            f'y="{y + 15}">{speedup(data["speedup"])}</text>'
        )
    parts.append(
        f'<line class="one" x1="{zero:.1f}" x2="{zero:.1f}" y1="4" y2="{height - 20}"/>'
        f'<text class="axis" x="{zero:.1f}" y="{height - 6}" text-anchor="middle">1x</text></svg>'
    )
    return "".join(parts)


def ratchet_chart(bench_id: str, data: dict[str, Any]) -> str:
    """Benchmark medians per run with the current ceiling; the shape shows the ratchet."""
    history = [(date.fromisoformat(d), float(v)) for d, v in data.get("history", [])]
    if len(history) < 2:
        return _empty(f"{bench_id} runs")
    width, height, left = 240, 70, 6
    values: list[float] = [v for _, v in history]
    if data.get("ceiling"):
        values.append(float(data["ceiling"]))
    low, high = min(values) * 0.95, max(values) * 1.02
    first, last = history[0][0], history[-1][0]
    span = max((last - first).days, 1)

    def x(day: date) -> float:
        return left + (width - 2 * left) * (day - first).days / span

    def y(value: float) -> float:
        return 6 + (height - 12) * (1 - (value - low) / (high - low))

    steps = []
    for index, (day, value) in enumerate(history):
        if index == 0:
            steps.append(f"M{x(day):.1f},{y(value):.1f}")
        else:
            steps.append(f"H{x(day):.1f} V{y(value):.1f}")
    parts = [
        f'<svg class="chart spark" viewBox="0 0 {width} {height}" role="img" '
        f'aria-label="{escape(bench_id)} median per run">'
    ]
    if data.get("ceiling"):
        cy = y(data["ceiling"])
        parts.append(f'<line class="ceiling" x1="0" x2="{width}" y1="{cy:.1f}" y2="{cy:.1f}"/>')
    parts.append(f'<path class="line" d="{" ".join(steps)}"/>')
    parts.append(
        f'<circle class="end" cx="{x(last):.1f}" cy="{y(history[-1][1]):.1f}" r="3"/></svg>'
    )
    return "".join(parts)


def _nice_range(low: float, high: float) -> tuple[float, float]:
    if high == low:
        return low * 0.9 if low else -1.0, high * 1.1 if high else 1.0
    pad = (high - low) * 0.08
    return max(low - pad, 0.0) if low >= 0 else low - pad, high + pad


def _ticks(low: float, high: float) -> list[float]:
    raw = (high - low) / 3
    magnitude = 10 ** math.floor(math.log10(raw))
    step = min((m * magnitude for m in (1, 2, 2.5, 5, 10) if m * magnitude >= raw), default=raw)
    start = math.ceil(low / step) * step
    ticks: list[float] = []
    value = start
    while value <= high + 1e-9 and len(ticks) < 6:
        ticks.append(round(value, 10))
        value += step
    return ticks


def _open(label: str) -> str:
    return f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="{escape(label)}">'


def _empty(label: str) -> str:
    return (
        f'<svg class="chart" viewBox="0 0 {W} 60" role="img" aria-label="{escape(label)}">'
        f'<text class="axis" x="{W / 2}" y="34" text-anchor="middle">not enough data '
        f"yet</text></svg>"
    )


def _label(day: date) -> str:
    return f"{day:%b} {day.day}"


def _short(text: str, limit: int) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"
