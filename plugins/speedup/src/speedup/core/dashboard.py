"""The dashboard page: one HTML file, inline CSS and SVG, no script.

`render_page` returns the body for a claude.ai Artifact (the host adds the document skeleton).
`render_document` wraps the same body in a full document for opening from disk.
Every string from sources or the change log is escaped; links accept http(s) only.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from html import escape
from typing import Any

from speedup.core.charts import journey_chart, ratchet_chart, speedup_bars
from speedup.core.markdown import to_html
from speedup.core.numbers import compact, p_value, pct, plain, speedup, with_unit
from speedup.core.writeup import SOURCES_HEADING

FONTS = (
    "https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,400;8..60,500;8..60,600"
    "&family=DM+Sans:opsz,wght@9..40,400;9..40,500;9..40,600"
    "&family=JetBrains+Mono:wght@400;500&display=swap"
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
/* Layout follows an engineering blog post: ivory paper, a serif headline over a sans lede,
   a meta column of dates, hairline rules between sections, oat panels for figures, and a
   clay accent kept for the headline number and the marks that matter. One column on phones. */
:root {
  --paper: #faf9f5; --panel: #f0eee6; --raised: #ffffff; --ink: #141413; --muted: #5e5d59;
  --faint: #87867f; --rule: #dedcd1; --rule-soft: #e8e6dc;
  --clay: #d97757; --accent-big: #c6613f; --accent-text: #a9502f;
  --series: #3d3d3a; --area: rgba(61, 61, 58, 0.07);
  --band-base: rgba(135, 134, 127, 0.13); --band-now: rgba(217, 119, 87, 0.13);
  --good: #3f7a66; --warn: #8a5a1c; --bad: #a8392f; --neutral: #5e5d59;
  --good-bg: #dfeae4; --warn-bg: #f2e6d2; --bad-bg: #f5ded9; --neutral-bg: #e8e6dc;
  --bar-good: #d97757; --bar-bad: #87867f;
  --display: "Source Serif 4", "Tiempos Headline", Georgia, "Times New Roman", serif;
  --body: "DM Sans", system-ui, "Segoe UI", Helvetica, Arial, sans-serif;
  --mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, monospace;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #1f1e1d; --panel: #262624; --raised: #30302e; --ink: #faf9f5; --muted: #b0aea5;
    --faint: #87867f; --rule: #3d3d3a; --rule-soft: #30302e;
    --clay: #d97757; --accent-big: #e08a6c; --accent-text: #e5947a;
    --series: #e8e6dc; --area: rgba(232, 230, 220, 0.07);
    --band-base: rgba(176, 174, 165, 0.10); --band-now: rgba(217, 119, 87, 0.16);
    --good: #8fc2ab; --warn: #e2b36f; --bad: #ec8f82; --neutral: #b0aea5;
    --good-bg: #24342d; --warn-bg: #3a2f1d; --bad-bg: #3d2522; --neutral-bg: #30302e;
    --bar-good: #d97757; --bar-bad: #73726c;
    color-scheme: dark;
  }
}
:root[data-theme="dark"] {
  --paper: #1f1e1d; --panel: #262624; --raised: #30302e; --ink: #faf9f5; --muted: #b0aea5;
  --faint: #87867f; --rule: #3d3d3a; --rule-soft: #30302e;
  --clay: #d97757; --accent-big: #e08a6c; --accent-text: #e5947a;
  --series: #e8e6dc; --area: rgba(232, 230, 220, 0.07);
  --band-base: rgba(176, 174, 165, 0.10); --band-now: rgba(217, 119, 87, 0.16);
  --good: #8fc2ab; --warn: #e2b36f; --bad: #ec8f82; --neutral: #b0aea5;
  --good-bg: #24342d; --warn-bg: #3a2f1d; --bad-bg: #3d2522; --neutral-bg: #30302e;
  --bar-good: #d97757; --bar-bad: #73726c;
  color-scheme: dark;
}
* { box-sizing: border-box; }
body { background: var(--paper); color: var(--ink); font: 16px/1.6 var(--body); margin: 0;
  -webkit-font-smoothing: antialiased; }
body::before { content: ""; position: fixed; inset: 0 0 auto; z-index: 10;
  height: env(safe-area-inset-top, 0px); background: var(--paper); }
.wrap { max-width: 1120px; margin: 0 auto; padding-block: 0 96px;
  padding-left: max(16px, env(safe-area-inset-left, 0px));
  padding-right: max(16px, env(safe-area-inset-right, 0px)); display: grid; gap: 0;
  grid-template-columns: minmax(0, 1fr); }
.wrap > *, section > * { min-width: 0; }
h1, h2, h3 { font-family: var(--display); font-weight: 500; letter-spacing: -0.015em;
  text-wrap: balance; margin: 0; line-height: 1.12; }
h1 { font-size: clamp(36px, 5.6vw, 56px); }
h2 { font-size: clamp(28px, 3.4vw, 36px); }
h3 { font-size: 21px; letter-spacing: -0.01em; }
a { color: inherit; text-decoration-color: var(--faint); text-underline-offset: 3px; }
a:hover { text-decoration-color: var(--ink); }
a:focus-visible { outline: 2px solid var(--clay); outline-offset: 2px; border-radius: 2px; }
.eyebrow { font: 500 13px/1.3 var(--body); color: var(--muted); letter-spacing: 0; }
.num { font-family: var(--body); font-variant-numeric: tabular-nums; }
nav { position: sticky; top: env(safe-area-inset-top, 0px); z-index: 5; background: var(--paper);
  border-bottom: 1px solid var(--rule-soft); display: flex; align-items: center; gap: 22px;
  overflow-x: auto; padding-block: 14px; font: 400 13px var(--body); }
nav .brand { color: var(--ink); font-weight: 500; margin-right: auto; white-space: nowrap; }
nav a { color: var(--muted); text-decoration: none; white-space: nowrap; }
nav a:hover { color: var(--ink); }
header { display: grid; grid-template-columns: minmax(0, 1fr) 210px; gap: 32px 48px;
  padding-block: 72px 64px; border-bottom: 1px solid var(--rule-soft); }
.hero { display: grid; gap: 22px; max-width: 600px; }
.mark { width: 132px; height: 132px; border-radius: 22px; background: var(--panel);
  display: grid; place-items: center; }
.mark svg { width: 74px; height: 74px; }
.mark .ink { fill: none; stroke: var(--ink); stroke-width: 2.4; stroke-linecap: round;
  stroke-linejoin: round; }
.mark .hand { stroke: var(--clay); stroke-width: 3; stroke-linecap: round; }
.mark .face { fill: var(--raised); }
.lede-big { margin: 0; font-size: 21px; line-height: 1.5; color: var(--muted); }
.facts { display: grid; gap: 20px; align-content: end; margin: 0; }
.facts div { display: grid; gap: 2px; }
.facts dt { font-size: 12px; color: var(--faint); }
.facts dd { margin: 0; font-size: 15px; }
section { display: grid; gap: 20px; padding-block: 64px;
  border-bottom: 1px solid var(--rule-soft); }
section:last-child { border-bottom: 0; }
section > .eyebrow + h2 { margin-top: -10px; }
.section-head { display: grid; gap: 10px; max-width: 680px; }
section p.lede { margin: 0; color: var(--muted); max-width: 64ch; font-size: 17px; }
.board { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1.5fr); gap: 40px;
  align-items: end; }
.split { display: grid; gap: 8px; align-content: start; }
.split .big { font: 500 clamp(80px, 13vw, 136px)/0.92 var(--display);
  letter-spacing: -0.03em; color: var(--accent-big); font-variant-numeric: tabular-nums; }
.split p { margin: 0; color: var(--muted); max-width: 38ch; font-size: 17px; }
.tiles { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 0;
  border-top: 1px solid var(--rule); }
.tile { padding: 16px 16px 18px 0; display: grid; gap: 4px; border-bottom: 1px solid var(--rule); }
.tile b { font: 500 34px/1 var(--display); letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums; }
.tile span { color: var(--muted); font-size: 13px; line-height: 1.4; }
figure { margin: 0; background: var(--panel); border-radius: 16px; padding: 24px 24px 20px;
  display: grid; gap: 14px; overflow-x: auto; }
figure svg.bars { min-width: 520px; }
figcaption { font-size: 13px; color: var(--muted); }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; }
.card { background: var(--panel); border-radius: 16px; padding: 20px;
  display: grid; gap: 12px; min-width: 0; align-content: start; }
.card-head { display: flex; justify-content: space-between; align-items: start; gap: 10px; }
.card-head h3 { font-size: 21px; }
.card .eyebrow { font: 400 12px var(--mono); color: var(--faint); }
.readout { display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px 14px; }
.readout .now { font: 500 32px/1 var(--display); letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums; }
.readout .was { color: var(--muted); font-size: 14px; }
.readout .x { font: 600 15px var(--body); color: var(--accent-text);
  font-variant-numeric: tabular-nums; }
.meta { display: flex; flex-wrap: wrap; gap: 4px 16px; color: var(--muted); font-size: 13px; }
.pill { display: inline-block; font: 500 12px/1 var(--body); padding: 6px 10px;
  border-radius: 999px; white-space: nowrap; }
.tone-good { color: var(--good); background: var(--good-bg); }
.tone-warn { color: var(--warn); background: var(--warn-bg); }
.tone-bad { color: var(--bad); background: var(--bad-bg); }
.tone-neutral { color: var(--neutral); background: var(--neutral-bg); }
svg.chart { width: 100%; height: auto; display: block; overflow: visible; }
svg.spark { max-width: 260px; }
svg.bars { max-width: 760px; }
.chart .grid { stroke: var(--rule); stroke-width: 1; }
.chart .axis, .chart .label, .chart .value, .chart .target-label { fill: var(--muted);
  font: 10px var(--body); }
.chart .label { font: 13px var(--body); fill: var(--ink); }
.chart .value { font: 600 13px var(--body); fill: var(--ink); }
.chart .line { fill: none; stroke: var(--series); stroke-width: 1.8; stroke-linejoin: round;
  stroke-linecap: round; }
.chart .area { fill: var(--area); stroke: none; }
.chart .end { fill: var(--clay); stroke: var(--panel); stroke-width: 2; }
.chart .target { stroke: var(--good); stroke-dasharray: 5 4; stroke-width: 1.4; }
.chart .target-label { fill: var(--good); font-weight: 500; }
.chart .ceiling { stroke: var(--bad); stroke-dasharray: 4 3; stroke-width: 1.2; }
.chart .band-baseline { fill: var(--band-base); }
.chart .band-current { fill: var(--band-now); }
.chart .ship line { stroke: var(--clay); stroke-width: 1.6; }
.chart .ship circle { fill: var(--clay); }
.chart .bar { rx: 3; }
.chart .bar-good { fill: var(--bar-good); }
.chart .bar-bad { fill: var(--bar-bad); }
.chart .one { stroke: var(--ink); stroke-width: 1; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; color: var(--muted); font-size: 13px; }
.legend i { display: inline-block; width: 14px; height: 10px; margin-right: 6px;
  vertical-align: -1px; border-radius: 2px; }
.legend .k-base { background: var(--band-base); }
.legend .k-now { background: var(--band-now); }
.legend .k-target { border-top: 2px dashed var(--good); height: 0; border-radius: 0; }
.legend .k-ship { background: var(--clay); width: 3px; }
.table-scroll { overflow-x: auto; border-top: 1px solid var(--rule); }
table { border-collapse: collapse; width: 100%; font-size: 14px; }
th, td { text-align: left; padding: 12px 14px 12px 0; border-bottom: 1px solid var(--rule-soft);
  vertical-align: top; }
th { font: 500 12px var(--body); color: var(--faint); }
td.num, th.num { text-align: right; white-space: nowrap; font-variant-numeric: tabular-nums; }
td .eyebrow { font: 400 12px var(--mono); color: var(--faint); }
#changes table { min-width: 860px; }
.table-scroll code { overflow-wrap: normal; white-space: nowrap; }
.alert { border-left: 3px solid var(--bad); background: var(--bad-bg); color: var(--ink);
  border-radius: 4px 12px 12px 4px; padding: 14px 18px; display: grid; gap: 6px; font-size: 15px; }
.alert strong { color: var(--bad); font-weight: 600; }
.writeup { display: grid; justify-items: start; }
.writeup > * { max-width: 640px; width: 100%; margin-inline: auto; }
.writeup .table-scroll { max-width: 760px; }
.writeup h2 { font-size: clamp(32px, 4.4vw, 44px); margin-block: 0 18px; }
.writeup h3 { font-size: 28px; margin-block: 44px 10px; }
.writeup h4 { font: 600 17px var(--body); margin-block: 26px 6px; }
.writeup p, .writeup li { font-size: 17px; line-height: 1.7; }
.writeup p { margin-block: 0 18px; }
.writeup blockquote { margin: 20px auto; padding: 4px 0 4px 20px;
  border-left: 3px solid var(--clay); color: var(--muted); font: 400 20px/1.5 var(--display); }
.writeup pre { background: var(--panel); padding: 16px; border-radius: 12px; overflow-x: auto; }
.writeup code { background: var(--panel); padding: 1px 5px; border-radius: 4px; }
.writeup pre code { background: none; padding: 0; }
.writeup details { margin-top: 36px; border-top: 1px solid var(--rule); padding-top: 14px; }
.writeup summary { cursor: pointer; font-size: 14px; color: var(--muted); }
.notes { margin: 0; padding-left: 18px; color: var(--muted); display: grid; gap: 8px;
  max-width: 80ch; font-size: 14px;
  grid-template-columns: minmax(0, 1fr); overflow-wrap: anywhere; }
code { font-family: var(--mono); font-size: 0.88em; overflow-wrap: anywhere; }
.card > code.cmd { display: block; white-space: pre; overflow-x: auto; overflow-wrap: normal;
  background: var(--raised); border-radius: 8px; padding: 8px 10px; font-size: 12px; }
@media (max-width: 760px) {
  header { grid-template-columns: minmax(0, 1fr); padding-block: 40px 40px; }
  .mark { width: 96px; height: 96px; border-radius: 18px; }
  .mark svg { width: 54px; height: 54px; }
  .facts { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  section { padding-block: 44px; }
  .board { grid-template-columns: minmax(0, 1fr); gap: 24px; }
  .grid { grid-template-columns: minmax(0, 1fr); }
  .tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  figure { padding: 16px; }
  .lede-big { font-size: 18px; }
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
        _nav(bool(writeup_markdown)),
        _header(metrics),
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
            '<section id="writeup"><div class="section-head"><div class="eyebrow">Write-up</div>'
            "</div>"
            f'<article class="writeup">{to_html(post)}{folded}</article></section>'
        )
    sections.append(_method(metrics))
    return f'<main class="wrap">{"".join(sections)}</main>'


def _header(metrics: dict[str, Any]) -> str:
    windows = metrics.get("windows") or {}
    baseline = windows.get("baseline")
    percentile = escape(metrics["percentile"])
    facts = [
        ("Data through", _day(metrics["as_of"]) if metrics.get("as_of") else "No data yet"),
        (
            "Baseline",
            f"{_day(baseline['since'])} to {_day(baseline['until'])}" if baseline else "Not set",
        ),
        ("Journeys", f"{len(metrics['journeys'])} at {metrics['percentile']}"),
        ("Generated", _stamp(metrics["generated_at"])),
    ]
    fact_html = "".join(
        f"<div><dt>{escape(label)}</dt><dd>{escape(value)}</dd></div>" for label, value in facts
    )
    return (
        '<header id="top"><div class="hero">'
        f'<div class="mark" aria-hidden="true">{_STOPWATCH}</div>'
        f"<h1>{escape(metrics['project'])} speed board</h1>"
        f'<p class="lede-big">Daily {percentile} from field data for each user journey, the '
        "changes shipped against them, and the guardrails that keep every win.</p></div>"
        f'<dl class="facts">{fact_html}</dl></header>'
    )


_STOPWATCH = (
    '<svg viewBox="0 0 64 64"><circle class="face ink" cx="32" cy="36" r="20"/>'
    '<path class="ink" d="M27 9h10M32 9v7M46 21l3-3M32 19.5v3M48.5 36h-3M32 52.5v-3M15.5 36h3"/>'
    '<path class="hand" d="M32 36l9-9"/><circle cx="32" cy="36" r="2.4" fill="currentColor"/>'
    "</svg>"
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
    return (
        '<nav><a class="brand" href="#top">speedup</a>'
        + "".join(f'<a href="#{a}">{t}</a>' for a, t in links)
        + "</nav>"
    )


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
        '<section id="overview"><div class="section-head"><div class="eyebrow">Overview</div>'
        "<h2>Where it stands</h2></div>"
        f"{alerts}"
        '<div class="board"><div class="split"><div class="eyebrow">Overall speedup</div>'
        f'<div class="big">{escape(big)}</div><p>{caption}</p></div>'
        f'<div class="tiles">{tile_html}</div></div>'
        f"<figure>{speedup_bars(metrics['journeys'])}"
        "<figcaption>Speedup by journey, baseline to now, on a log scale. Gray bars are "
        "slower than the baseline.</figcaption></figure></section>"
    )


def _alerts(metrics: dict[str, Any]) -> str:
    rows = []
    for journey_id, j in metrics["journeys"].items():
        if j.get("regressed"):
            rows.append(
                f"<div><strong>{escape(j['name'])} regressed:</strong> "
                f"{escape(with_unit(j.get('previous'), j['unit']))} to "
                f"{escape(with_unit(j.get('current'), j['unit']))} "
                f"({escape(_pace(j.get('vs_previous_pct')))}, p "
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
            f"<span>{escape(_versus_last(j.get('vs_previous_pct')))}</span>"
            f"<span>{_count(len(marks.get(journey_id, [])), 'change')}</span></div>"
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
            "<code>speedup log</code>.</p></section>"
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
                    f"({escape(_pace(row['improvement_pct']))}, p "
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
            f'<span class="x">{escape(pct(_negated(b.get("ceiling_reduction_pct"))))} since '
            "first</span></div>"
            f"{ratchet_chart(bench_id, b)}"
            f'<div class="meta"><span>first '
            f"{escape(with_unit(b.get('original'), b['unit']))}</span>"
            f"<span>{b['runs']} runs</span><span>cv "
            f"{escape(pct(b.get('latest_cv_pct'), False))}</span>"
            f"<span>journeys {escape(', '.join(b['journeys']) or 'none')}</span></div>"
            f'<code class="cmd">{escape(b["command"])}</code></article>'
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


def _pace(value: float | None) -> str:
    """An improvement percentage in words: 52.1% faster, 20.1% slower."""
    if value is None:
        return "n/a"
    if round(value, 1) == 0:
        return "no change"
    return f"{pct(abs(value), False)} {'faster' if value > 0 else 'slower'}"


def _versus_last(value: float | None) -> str:
    if value is None:
        return "no previous window"
    pace = _pace(value)
    return f"{pace} since last window" if pace == "no change" else f"{pace} than last window"


def _count(n: int, noun: str) -> str:
    return f"{n} {noun}" if n == 1 else f"{n} {noun}s"


def _stamp(value: str) -> str:
    try:
        moment = datetime.fromisoformat(value)
    except ValueError:
        return value
    return f"{moment:%b} {moment.day}, {moment.year}, {moment:%H:%M} UTC"


def _day(value: str) -> str:
    day = date.fromisoformat(value)
    return f"{day:%b} {day.day}, {day.year}"
