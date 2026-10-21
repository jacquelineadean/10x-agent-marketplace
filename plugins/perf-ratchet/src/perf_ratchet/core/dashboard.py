"""The dashboard page: one HTML file, inline CSS and SVG, no script.

`render_page` returns the body for a claude.ai Artifact (the host adds the document skeleton).
`render_document` wraps the same body in a full document for opening from disk.
Every string from sources or the change log is escaped; links accept http(s) only.
"""

from __future__ import annotations

import re
from datetime import date
from html import escape
from typing import Any

from perf_ratchet.core.charts import journey_chart, ratchet_chart, speedup_bars
from perf_ratchet.core.markdown import to_html
from perf_ratchet.core.numbers import compact, p_value, pct, plain, speedup, with_unit
from perf_ratchet.core.writeup import SOURCES_HEADING

FONTS = (
    "https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700"
    "&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap"
)
_SAFE_URL = re.compile(r"^https?://[^\s<>\"']+$")
_STATUS_LABEL = {
    "at-target": "At target",
    "improving": "Improving",
    "flat": "Flat",
    "slower": "Slower than baseline",
    "regressed": "Regressed",
    "measuring": "Measuring",
    "stale": "No recent data",
    "no-data": "No data",
}
_STATUS_TONE = {
    "at-target": "good",
    "improving": "good",
    "flat": "neutral",
    "measuring": "neutral",
    "slower": "warn",
    "stale": "warn",
    "no-data": "neutral",
    "regressed": "bad",
}

STYLE = """
/* Layout: a timing-board summary band, journey small multiples, then the change ledger,
   the guardrail rack, the write-up and the method notes. One column on phones. */
:root {
  --paper: #eef1f4; --panel: #ffffff; --ink: #15202b; --muted: #566472; --rule: #d3dae1;
  --accent: #d24a12; --series: #1f4e79; --area: rgba(31, 78, 121, 0.10);
  --band-base: rgba(86, 100, 114, 0.10); --band-now: rgba(210, 74, 18, 0.09);
  --good: #17784a; --warn: #9a5b00; --bad: #bf2b2b; --neutral: #566472;
  --good-bg: #e2f2e9; --warn-bg: #f7ecd9; --bad-bg: #f8e1e1; --neutral-bg: #e6eaee;
  --display: "Barlow Condensed", "Arial Narrow", "Roboto Condensed", sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #0f1519; --panel: #172026; --ink: #e5ecf1; --muted: #93a3b0; --rule: #2a3742;
    --accent: #ff7a3d; --series: #8cc4f2; --area: rgba(140, 196, 242, 0.12);
    --band-base: rgba(147, 163, 176, 0.10); --band-now: rgba(255, 122, 61, 0.10);
    --good: #5fd08f; --warn: #f0b048; --bad: #ff7b7b; --neutral: #93a3b0;
    --good-bg: #173326; --warn-bg: #3a2c12; --bad-bg: #3d1c1c; --neutral-bg: #222d35;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #0f1519; --panel: #172026; --ink: #e5ecf1; --muted: #93a3b0; --rule: #2a3742;
  --accent: #ff7a3d; --series: #8cc4f2; --area: rgba(140, 196, 242, 0.12);
  --band-base: rgba(147, 163, 176, 0.10); --band-now: rgba(255, 122, 61, 0.10);
  --good: #5fd08f; --warn: #f0b048; --bad: #ff7b7b; --neutral: #93a3b0;
  --good-bg: #173326; --warn-bg: #3a2c12; --bad-bg: #3d1c1c; --neutral-bg: #222d35;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--paper); color: var(--ink); font: 15px/1.55 var(--body); margin: 0; }
.wrap { max-width: 1180px; margin: 0 auto; padding-block: 28px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 40px;
  grid-template-columns: minmax(0, 1fr); }
.wrap > *, section > * { min-width: 0; }
h1, h2, h3 { font-family: var(--display); font-weight: 600; letter-spacing: 0.01em;
  text-wrap: balance; margin: 0; line-height: 1.1; }
h1 { font-size: clamp(30px, 5vw, 46px); }
h2 { font-size: 28px; }
h3 { font-size: 20px; }
a { color: var(--series); }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.eyebrow { font: 500 12px/1.2 var(--mono); text-transform: uppercase; letter-spacing: 0.12em;
  color: var(--muted); }
.num { font-family: var(--mono); font-variant-numeric: tabular-nums; }
nav { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--paper);
  border-bottom: 1px solid var(--rule); display: flex; gap: 18px; overflow-x: auto;
  padding-block: 10px; font: 500 13px var(--mono); }
nav a { color: var(--muted); text-decoration: none; white-space: nowrap; }
nav a:hover { color: var(--ink); }
header { display: grid; gap: 10px; }
.board { display: grid; grid-template-columns: minmax(0, 1.3fr) minmax(0, 2fr); gap: 24px;
  background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 24px; }
.split { display: grid; gap: 6px; align-content: start; }
.split .big { font: 700 clamp(64px, 11vw, 112px)/0.9 var(--display); color: var(--accent);
  font-variant-numeric: tabular-nums; }
.split p { margin: 0; color: var(--muted); max-width: 40ch; }
.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 1px;
  align-self: start;
  background: var(--rule); border: 1px solid var(--rule); border-radius: 4px; overflow: hidden; }
.tile { background: var(--panel); padding: 14px 16px; display: grid; gap: 4px; }
.tile b { font: 600 30px/1 var(--display); font-variant-numeric: tabular-nums; }
.tile span { color: var(--muted); font-size: 13px; }
section { display: grid; gap: 16px; }
section > p.lede { margin: 0; color: var(--muted); max-width: 70ch; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 16px; }
.card { background: var(--panel); border: 1px solid var(--rule); border-radius: 6px; padding: 16px;
  display: grid; gap: 10px; min-width: 0; align-content: start; }
.card-head { display: flex; justify-content: space-between; align-items: start; gap: 10px; }
.card-head h3 { font-size: 19px; }
.readout { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }
.readout .now { font: 600 28px/1 var(--display); font-variant-numeric: tabular-nums; }
.readout .was { color: var(--muted); font: 13px var(--mono); }
.readout .x { font: 600 16px var(--mono); color: var(--accent); }
.meta { display: flex; flex-wrap: wrap; gap: 4px 14px; color: var(--muted);
  font: 12px var(--mono); }
.pill { display: inline-block; font: 600 11px/1 var(--mono); text-transform: uppercase;
  letter-spacing: 0.06em; padding: 5px 8px; border-radius: 999px; white-space: nowrap; }
.tone-good { color: var(--good); background: var(--good-bg); }
.tone-warn { color: var(--warn); background: var(--warn-bg); }
.tone-bad { color: var(--bad); background: var(--bad-bg); }
.tone-neutral { color: var(--neutral); background: var(--neutral-bg); }
svg.chart { width: 100%; height: auto; display: block; overflow: visible; }
svg.spark { max-width: 240px; }
svg.bars { max-width: 760px; }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
.chart .axis, .chart .label, .chart .value, .chart .target-label { fill: var(--muted);
  font: 10px var(--mono); }
.chart .label { font: 12px var(--body); fill: var(--ink); }
.chart .value { font: 600 12px var(--mono); fill: var(--ink); }
.chart .line { fill: none; stroke: var(--series); stroke-width: 1.8; stroke-linejoin: round; }
.chart .area { fill: var(--area); stroke: none; }
.chart .end { fill: var(--accent); stroke: var(--panel); stroke-width: 1.5; }
.chart .target { stroke: var(--good); stroke-dasharray: 5 4; stroke-width: 1.4; }
.chart .target-label { fill: var(--good); }
.chart .ceiling { stroke: var(--bad); stroke-dasharray: 4 3; stroke-width: 1.2; }
.chart .band-baseline { fill: var(--band-base); }
.chart .band-current { fill: var(--band-now); }
.chart .ship line { stroke: var(--accent); stroke-width: 1.4; }
.chart .ship circle { fill: var(--accent); }
.chart .bar-good { fill: var(--series); }
.chart .bar-bad { fill: var(--bad); }
.chart .one { stroke: var(--muted); stroke-width: 1; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; color: var(--muted);
  font: 12px var(--mono); }
.legend i { display: inline-block; width: 14px; height: 10px; margin-right: 6px;
  vertical-align: -1px; }
.legend .k-base { background: var(--band-base); border: 1px solid var(--rule); }
.legend .k-now { background: var(--band-now); border: 1px solid var(--rule); }
.legend .k-target { border-top: 2px dashed var(--good); height: 0; }
.legend .k-ship { background: var(--accent); width: 3px; }
.table-scroll { overflow-x: auto; background: var(--panel); border: 1px solid var(--rule);
  border-radius: 6px; }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 9px 12px; border-bottom: 1px solid var(--rule);
  vertical-align: top; }
th { font: 500 11px var(--mono); text-transform: uppercase; letter-spacing: 0.08em;
  color: var(--muted); }
td.num, th.num { text-align: right; white-space: nowrap; }
tbody tr:last-child td { border-bottom: 0; }
#changes table { min-width: 860px; }
.table-scroll code { overflow-wrap: normal; white-space: nowrap; }
.alert { border: 1px solid var(--bad); background: var(--bad-bg); color: var(--ink);
  border-radius: 6px;
  padding: 12px 16px; display: grid; gap: 4px; }
.alert strong { color: var(--bad); }
.writeup { background: var(--panel); border: 1px solid var(--rule); border-radius: 6px;
  padding: 28px clamp(16px, 4vw, 48px); }
.writeup > * { max-width: 68ch; }
.writeup .table-scroll { max-width: 100%; }
.writeup h2 { font-size: 34px; margin-block: 0 12px; }
.writeup h3 { font-size: 24px; margin-block: 28px 8px; }
.writeup h4 { font: 600 16px var(--body); margin-block: 20px 6px; }
.writeup p, .writeup li { font-size: 16px; line-height: 1.65; }
.writeup blockquote { margin: 16px 0; padding-left: 16px; border-left: 3px solid var(--accent);
  color: var(--muted); }
.writeup pre { background: var(--paper); padding: 12px; border-radius: 4px; overflow-x: auto; }
.writeup details { margin-top: 28px; border-top: 1px solid var(--rule); padding-top: 12px; }
.writeup summary { cursor: pointer; font: 500 13px var(--mono); color: var(--muted); }
.notes { margin: 0; padding-left: 18px; color: var(--muted); display: grid; gap: 6px;
  max-width: 80ch;
  grid-template-columns: minmax(0, 1fr); overflow-wrap: anywhere; }
code { font-family: var(--mono); font-size: 0.92em; overflow-wrap: anywhere; }
@media (max-width: 720px) {
  .board { grid-template-columns: minmax(0, 1fr); padding: 16px; }
  .grid { grid-template-columns: minmax(0, 1fr); }
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (prefers-reduced-motion: reduce) { * { scroll-behavior: auto; } }
"""


def render_page(metrics: dict[str, Any], writeup_markdown: str | None = None) -> str:
    """Artifact body: title, fonts, style and content, no document skeleton."""
    title = escape(f"{metrics['project']} speed board")
    return "\n".join(
        [
            f"<title>{title}</title>",
            '<meta name="claude:viewport-fit-sides" content="cover">',
            f'<link rel="stylesheet" href="{FONTS}">',
            f"<style>{STYLE}</style>",
            _body(metrics, writeup_markdown),
        ]
    )


def render_document(metrics: dict[str, Any], writeup_markdown: str | None = None) -> str:
    """A full document for opening from disk; fonts fall back to local faces offline."""
    return (
        '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        f"{render_page(metrics, writeup_markdown)}\n</html>\n"
    )


def _body(metrics: dict[str, Any], writeup_markdown: str | None) -> str:
    sections = [
        _header(metrics),
        _nav(bool(writeup_markdown)),
        _overview(metrics),
        _journeys(metrics),
        _next(metrics),
        _changes(metrics),
        _guardrails(metrics),
    ]
    if writeup_markdown:
        post, _, sources = writeup_markdown.partition(SOURCES_HEADING)
        folded = (
            f"<details><summary>Numbers and their sources</summary>{to_html(sources)}</details>"
            if sources
            else ""
        )
        sections.append(
            '<section id="writeup"><div class="eyebrow">Write-up</div>'
            f'<article class="writeup">{to_html(post)}{folded}</article></section>'
        )
    sections.append(_method(metrics))
    return f'<main class="wrap">{"".join(sections)}</main>'


def _header(metrics: dict[str, Any]) -> str:
    windows = metrics.get("windows") or {}
    baseline = windows.get("baseline")
    span = (
        f"Baseline {_day(baseline['since'])} to {_day(baseline['until'])}. "
        if baseline
        else "No baseline yet. "
    )
    as_of = f"Data through {_day(metrics['as_of'])}." if metrics.get("as_of") else "No data yet."
    return (
        '<header id="top"><div class="eyebrow">perf-ratchet · '
        f"{escape(metrics['percentile'])} field data</div>"
        f"<h1>{escape(metrics['project'])} speed board</h1>"
        f'<div class="meta"><span>{escape(span + as_of)}</span>'
        f"<span>Generated {escape(metrics['generated_at'])}</span></div></header>"
    )


def _nav(has_writeup: bool) -> str:
    links = [
        ("overview", "Overview"),
        ("journeys", "Journeys"),
        ("next", "Next"),
        ("changes", "Changes"),
        ("guardrails", "Guardrails"),
    ]
    if has_writeup:
        links.append(("writeup", "Write-up"))
    links.append(("method", "Method"))
    return "<nav>" + "".join(f'<a href="#{a}">{t}</a>' for a, t in links) + "</nav>"


def _overview(metrics: dict[str, Any]) -> str:
    h = metrics["headline"]
    big = speedup(h.get("geomean_speedup")) if "geomean_speedup" in h else "n/a"
    caption = (
        f"faster on average across {h['journeys_measured']} journeys, "
        f"{escape(metrics['percentile'])} now against the baseline (geometric mean)."
        if "geomean_speedup" in h
        else "Measure at least a baseline and a current window to see a speedup."
    )
    tiles = [
        (f"{h['journeys_at_target']}/{h['journeys_with_target']}", "journeys at target"),
        (str(h["changes_shipped"]), f"changes shipped of {h['changes']} logged"),
        (str(h["changes_improved"]), "changes with a measured win"),
        (str(h["journeys_regressed"]), "regressions this window"),
        (
            pct(h.get("median_ceiling_reduction_pct"), False),
            f"median ceiling cut over {h['guardrails_with_ceiling']} guardrails",
        ),
        (f"{h['flags_open']}", f"flags still open of {h['flags_added']}"),
    ]
    tile_html = "".join(
        f'<div class="tile"><b>{escape(value)}</b><span>{escape(label)}</span></div>'
        for value, label in tiles
    )
    alerts = _alerts(metrics)
    return (
        '<section id="overview">'
        f"{alerts}"
        '<div class="board"><div class="split"><div class="eyebrow">Overall speedup</div>'
        f'<div class="big">{escape(big)}</div><p>{caption}</p></div>'
        f'<div class="tiles">{tile_html}</div></div>'
        '<div class="card"><div class="eyebrow">Speedup by journey, baseline to now (log '
        "scale)</div>"
        f"{speedup_bars(metrics['journeys'])}</div></section>"
    )


def _alerts(metrics: dict[str, Any]) -> str:
    rows = []
    for journey_id, j in metrics["journeys"].items():
        if j.get("regressed"):
            rows.append(
                f"<div><strong>{escape(j['name'])} regressed:</strong> "
                f"{escape(with_unit(j.get('previous'), j['unit']))} to "
                f"{escape(with_unit(j.get('current'), j['unit']))} "
                f"({escape(pct(j.get('vs_previous_pct')))}, p "
                f"{escape(p_value(j.get('vs_previous_p')))}) "
                f"against the previous window. <code>{escape(journey_id)}</code></div>"
            )
    for bench_id, b in metrics["benchmarks"].items():
        if b.get("within_ceiling") is False:
            rows.append(
                f"<div><strong>{escape(bench_id)} is over its ceiling:</strong> latest "
                f"{escape(with_unit(b.get('latest'), b['unit']))} against "
                f"{escape(with_unit(b.get('ceiling'), b['unit']))}.</div>"
            )
    return f'<div class="alert" role="status">{"".join(rows)}</div>' if rows else ""


def _journeys(metrics: dict[str, Any]) -> str:
    windows = metrics.get("windows") or {}
    marks: dict[str, list[dict[str, Any]]] = {}
    for change in metrics["changes"]:
        if change["shipped"]:
            for journey_id in change["journeys"]:
                marks.setdefault(journey_id, []).append(change)
    cards = []
    for journey_id, j in metrics["journeys"].items():
        status = j.get("status", "no-data")
        pill = (
            f'<span class="pill tone-{_STATUS_TONE.get(status, "neutral")}">'
            f"{_STATUS_LABEL.get(status, status)}</span>"
        )
        readout = (
            f'<div class="readout"><span class="now '
            f'num">{escape(with_unit(j.get("current"), j["unit"]))}</span>'
            f'<span class="was">from {escape(with_unit(j.get("baseline"), j["unit"]))}</span>'
            f'<span class="x">{escape(speedup(j.get("speedup")))}</span></div>'
        )
        target = (
            f"<span>target {escape(with_unit(j['target'], j['unit']))}</span>"
            if j.get("target")
            else "<span>no target set</span>"
        )
        gap = (
            f"<span>{escape(pct(j['gap_to_target_pct'], False))} over target</span>"
            if j.get("gap_to_target_pct")
            else ""
        )
        meta = (
            f'<div class="meta">{target}{gap}'
            f"<span>vs last window {escape(pct(j.get('vs_previous_pct')))}</span>"
            f"<span>{len(marks.get(journey_id, []))} changes</span></div>"
        )
        cards.append(
            f'<article class="card" id="j-{escape(journey_id)}"><div class="card-head">'
            f'<div><div class="eyebrow">{escape(journey_id)}</div>'
            f"<h3>{escape(j['name'])}</h3></div>"
            f"{pill}</div>{readout}"
            f"{journey_chart(journey_id, j, windows, marks.get(journey_id, []))}{meta}</article>"
        )
    legend = (
        '<div class="legend"><span><i class="k-base"></i>baseline window</span>'
        '<span><i class="k-now"></i>current window</span>'
        '<span><i class="k-target"></i>target</span><span><i class="k-ship"></i>change '
        "shipped</span></div>"
    )
    return (
        '<section id="journeys"><div class="eyebrow">Journeys</div>'
        "<h2>Each journey, day by day</h2>"
        f'<p class="lede">Daily {escape(metrics["percentile"])} from field data. A journey is one '
        f"thing a "
        "user does, timed from their side of the screen. Values are the median of the window's "
        "days.</p>"
        f'{legend}<div class="grid">{"".join(cards)}</div></section>'
    )


def _next(metrics: dict[str, Any]) -> str:
    rows = metrics["priorities"]
    if not rows:
        body = (
            '<p class="lede">Every journey with a target meets it. '
            "Raise a target or add a journey.</p>"
        )
    else:
        body_rows = "".join(
            f'<tr><td class="num">{i + 1}</td>'
            f"<td>{escape(metrics['journeys'][r['journey']]['name'])}</td>"
            f'<td class="num">{escape(pct(r["gap_to_target_pct"], False))}</td>'
            f'<td class="num">{escape(plain(r["weight"]))}</td><td '
            f'class="num">{escape(plain(r["score"]))}</td>'
            f'<td><span class="pill tone-{_STATUS_TONE.get(r["status"], "neutral")}">'
            f"{_STATUS_LABEL.get(r['status'], r['status'])}</span></td></tr>"
            for i, r in enumerate(rows)
        )
        body = (
            '<div class="table-scroll"><table><thead><tr><th class="num">#</th><th>Journey</th>'
            '<th class="num">Over target</th><th class="num">Weight</th><th class="num">Score</th>'
            f"<th>Status</th></tr></thead><tbody>{body_rows}</tbody></table></div>"
        )
    return (
        '<section id="next"><div class="eyebrow">Where to look next</div>'
        "<h2>Largest weighted gaps</h2>"
        '<p class="lede">Score is the gap to target times the journey weight. Regressions come '
        "first.</p>"
        f"{body}</section>"
    )


def _changes(metrics: dict[str, Any]) -> str:
    changes = list(reversed(metrics["changes"]))
    if not changes:
        return (
            '<section id="changes"><div class="eyebrow">Changes</div><h2>Change ledger</h2>'
            '<p class="lede">No changes logged yet. Log each optimization with '
            "<code>perf-ratchet log</code>.</p></section>"
        )
    rows = []
    for change in changes:
        title = escape(change["title"])
        if change["pr"] and _SAFE_URL.match(change["pr"]):
            link = escape(change["pr"])
            title = f'<a href="{link}" rel="noopener noreferrer" target="_blank">{title}</a>'
        effects = []
        for row in change["impact"]:
            if "improvement_pct" in row:
                tone = {"improved": "good", "regressed": "bad"}.get(row["verdict"], "neutral")
                effects.append(
                    f'<div><span class="pill tone-{tone}">{escape(row["verdict"])}</span> '
                    f"<code>{escape(row['journey'])}</code> "
                    f'<span class="num">{escape(with_unit(row["before"], row["unit"]))} → '
                    f"{escape(with_unit(row['after'], row['unit']))} "
                    f"({escape(pct(row['improvement_pct']))}, p "
                    f"{escape(p_value(row['p']))})</span></div>"
                )
            else:
                effects.append(
                    f"<div><code>{escape(row['journey'])}</code> {escape(row['verdict'])}</div>"
                )
        proxy = ""
        if "proxy" in change:
            p = change["proxy"]
            proxy = (
                f'<span class="num">{escape(compact(p["before"]))} → {escape(compact(p["after"]))} '
                f"({escape(pct(-p['reduction_pct']))})</span>"
                f"<br><code>{escape(p['benchmark'])}</code>"
            )
        shipped = _day(change["shipped"]) if change["shipped"] else "not shipped"
        flag = escape(change["flag"]) if change["flag"] else "none"
        if change["flag"]:
            flag += " (removed)" if change["flag_removed"] else " (open)"
        overlap = (
            f'<div class="meta">shares a journey with {escape(", ".join(change["overlaps"]))}</div>'
            if change["overlaps"]
            else ""
        )
        rows.append(
            f'<tr><td class="num">{escape(shipped)}</td>'
            f'<td><div class="eyebrow">{escape(change["id"])}</div>{title}{overlap}</td>'
            f"<td>{''.join(effects)}</td><td>{proxy}</td>"
            f'<td>{escape(change["stage"])}<br><span class="meta">{flag}</span></td></tr>'
        )
    return (
        '<section id="changes"><div class="eyebrow">Changes</div><h2>Change ledger</h2>'
        '<p class="lede">Field effect compares the days before and after each ship day with a rank '
        "test. The proxy column is the deterministic benchmark the change was built against.</p>"
        '<div class="table-scroll"><table><thead><tr><th class="num">Shipped</th><th>Change</th>'
        "<th>Field effect</th><th>Proxy</th><th>Rollout and flag</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></section>"
    )


def _guardrails(metrics: dict[str, Any]) -> str:
    benchmarks = metrics["benchmarks"]
    if not benchmarks:
        return (
            '<section id="guardrails"><div class="eyebrow">Guardrails</div><h2>Ratchet</h2>'
            '<p class="lede">No benchmarks yet. A benchmark is a command that prints a stable '
            "number "
            "for a hot path, such as an instruction count.</p></section>"
        )
    cards = []
    for bench_id, b in benchmarks.items():
        if "within_ceiling" not in b:
            tone, label = "neutral", "No run yet"
        elif not b["within_ceiling"]:
            tone, label = "bad", "Over ceiling"
        elif b.get("noisy"):
            tone, label = "warn", "Noisy"
        else:
            tone, label = "good", "Holding"
        cards.append(
            f'<article class="card"><div class="card-head"><div><div '
            f'class="eyebrow">{escape(bench_id)}</div>'
            f'<h3>{escape(b["name"])}</h3></div><span class="pill tone-{tone}">{label}</span></div>'
            f'<div class="readout"><span class="now '
            f'num">{escape(with_unit(b.get("latest"), b["unit"]))}</span>'
            f'<span class="was">ceiling {escape(with_unit(b.get("ceiling"), b["unit"]))}</span>'
            f'<span class="x">{escape(pct(_negated(b.get("ceiling_reduction_pct"))))}</span></div>'
            f"{ratchet_chart(bench_id, b)}"
            f'<div class="meta"><span>first '
            f"{escape(with_unit(b.get('original'), b['unit']))}</span>"
            f"<span>{b['runs']} runs</span><span>cv "
            f"{escape(pct(b.get('latest_cv_pct'), False))}</span>"
            f"<span>journeys {escape(', '.join(b['journeys']) or 'none')}</span></div>"
            f"<code>{escape(b['command'])}</code></article>"
        )
    return (
        '<section id="guardrails"><div class="eyebrow">Guardrails</div><h2>The ratchet</h2>'
        '<p class="lede">Wall-clock time is too noisy to gate code on, so each hot path gets a '
        "deterministic proxy. CI fails a change that pushes a proxy over its ceiling, and a daily "
        "job "
        "lowers the ceiling whenever the number drops. The dashed line is the ceiling.</p>"
        f'<div class="grid">{"".join(cards)}</div></section>'
    )


def _method(metrics: dict[str, Any]) -> str:
    sources = "".join(
        f"<li><code>{escape(k)}</code>: {escape(j['source'])}</li>"
        for k, j in metrics["journeys"].items()
    )
    notes = "".join(f"<li>{escape(n)}</li>" for n in [*metrics["limits"], *metrics["warnings"]])
    return (
        '<section id="method"><div class="eyebrow">Method and sources</div><h2>How these numbers '
        "are made</h2>"
        f'<ul class="notes">{sources}</ul><ul class="notes">{notes}</ul></section>'
    )


def _negated(value: float | None) -> float | None:
    """A reduction shown as a signed change: a 5% cut reads -5%, a 5% rise +5%."""
    return None if value is None else -value


def _day(value: str) -> str:
    day = date.fromisoformat(value)
    return f"{day:%b} {day.day}, {day.year}"
