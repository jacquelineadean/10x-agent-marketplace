import re
from datetime import UTC, date, datetime, timedelta

from speedup.core.budget import estimate_budget
from speedup.core.dashboard import render_document, render_page
from speedup.core.digest import DIGEST_CAP_BYTES, render_digest
from speedup.core.markdown import to_html
from speedup.core.model import BenchRun, Change
from speedup.core.report import build_metrics, lookup
from speedup.core.writeup import bare_numbers, fill, sources_section
from speedup_helpers import project, steps

START = date(2026, 8, 1)
NOW = datetime(2026, 10, 1, tzinfo=UTC)


def _metrics(title: str = "Static composer", changes: int = 1) -> dict:  # type: ignore[type-arg]
    p = project()
    history = {
        "load": {
            pt.day.isoformat(): pt.value
            for pt in steps(START, 50, [(0, 1200.0), (20, 500.0)], wobble=0.02)
        },
        "throughput": {
            pt.day.isoformat(): pt.value for pt in steps(START, 50, [(0, 200.0)], wobble=0.01)
        },
    }
    log = [
        Change(
            f"c-{i + 1:04d}",
            title,
            ["load"],
            shipped=START + timedelta(days=19),
            pr="https://github.com/acme/web/pull/1",
            flag="static_composer",
            stage="100%",
            benchmark="tree",
            proxy_before=2000,
            proxy_after=1000,
        )
        for i in range(changes)
    ]
    runs = [
        BenchRun("tree", START + timedelta(days=i), (1000.0 - i,), 1000.0 - i, 0.2)
        for i in range(5)
    ]
    return build_metrics(p, history, log, runs, NOW)


def test_metrics_carry_schema_version_windows_and_keys_the_digest_cites() -> None:
    metrics = _metrics()
    assert metrics["schema_version"] == 1
    assert metrics["windows"]["baseline"] == {
        "since": "2026-08-01",
        "until": "2026-08-07",
        "days": 7,
    }
    digest = render_digest(metrics)
    for key in re.findall(r"\((journeys|headline|changes|benchmarks)\.([\w.-]+)", digest):
        dotted = ".".join(key).split(",")[0].strip()
        if dotted.endswith(("*", ".")):
            continue
        lookup(metrics, dotted)
    assert "(journeys.load.*)" in digest or "journeys.load.*" in digest


def test_lookup_reaches_change_rows_by_id_and_journey() -> None:
    metrics = _metrics()
    assert lookup(metrics, "changes.c-0001.impact.load.verdict") == "improved"
    assert lookup(metrics, "changes.c-0001.proxy.reduction_pct") == 50.0


def test_digest_never_exceeds_the_cap_and_keeps_the_largest_effects() -> None:
    metrics = _metrics(title="A long change title " * 9, changes=120)
    digest = render_digest(metrics)
    assert len(digest.encode("utf-8")) <= DIGEST_CAP_BYTES
    assert "largest measured effects kept" in digest
    assert 0 < digest.count("- c-0") < 120


def test_dashboard_escapes_source_text_and_has_no_script() -> None:
    metrics = _metrics(title='<script>alert("x")</script> & <b>bold</b>')
    page = render_page(metrics, "## Post\n\n<img src=x onerror=alert(1)> **bold**")
    assert "<script" not in page.lower()
    assert "&lt;script&gt;" in page
    assert "<img" not in page
    assert "<strong>bold</strong>" in page
    assert page.startswith("<title>test-app speed board</title>")
    assert 'href="https://github.com/acme/web/pull/1"' in page
    for href in re.findall(r'href="([^"]+)"', page):
        assert href.startswith(("https://", "#"))


def test_dashboard_defines_light_and_dark_tokens_and_a_document_wrapper() -> None:
    page = render_page(_metrics())
    assert ':root:not([data-theme="light"])' in page and ':root[data-theme="dark"]' in page
    assert "body { background: var(--paper)" in page
    assert "env(safe-area-inset-left" in page
    document = render_document(_metrics())
    assert document.startswith("<!doctype html>")
    assert 'id="writeup"' not in document


def test_writeup_tokens_fill_with_units_and_formats() -> None:
    metrics = _metrics()
    filled = fill(
        "Load fell from {{journeys.load.baseline}} to {{journeys.load.current}}, "
        "{{journeys.load.speedup}} faster ({{journeys.load.improvement_pct}}). "
        "In seconds: {{journeys.load.baseline|s}}. Proxy cut "
        "{{changes.c-0001.proxy.reduction_pct}}. "
        "Ceiling {{benchmarks.tree.ceiling}}. Missing {{journeys.nope.current}}.",
        metrics,
    )
    assert "from 1,200 ms to 500 ms, 2.4x faster (58.3%)" in filled.text
    assert "In seconds: 1.2 s" in filled.text
    assert "Proxy cut 50%" in filled.text
    assert "Ceiling 1 K instructions" in filled.text
    assert filled.unknown == ["journeys.nope.current"]
    assert filled.bare == []
    assert "| `journeys.load.speedup` | 2.4x |" in sources_section(filled)


def test_numbers_typed_by_hand_are_listed_but_dates_ids_and_code_are_not() -> None:
    text = (
        "# Made it 3x faster\n1. Shipped on 2026-08-11 as c-0001 in 2026 at p75.\n"
        "We cut 48% of instructions and saved 120 ms in UTF-16 strings. "
        "See `node --max-old-space-size=4096`."
    )
    assert bare_numbers(text) == ["48%", "120 ms"]


def test_markdown_renders_tables_lists_and_safe_links_only() -> None:
    html = to_html(
        "## Results\n\n| Journey | Speedup |\n| --- | --- |\n| Load | 5x |\n\n"
        "- one\n- two\n\n[ok](https://claude.dev/blog) [bad](javascript:alert(1))\n\n"
        "<!-- note -->\n```\n<b>code</b>\n```"
    )
    assert "<h3>Results</h3>" in html
    assert "<td>Load</td>" in html and "<ul><li>one</li><li>two</li></ul>" in html
    assert '<a href="https://claude.dev/blog"' in html
    assert "javascript:" not in html.split("[bad]")[0] and 'href="javascript' not in html
    assert "note" not in html
    assert "&lt;b&gt;code&lt;/b&gt;" in html


def test_budget_sums_five_parts_against_the_cap() -> None:
    budget = estimate_budget(8000, 4000, 25_000)
    assert budget["parts"]["digest"] == 2000
    assert budget["estimated_tokens"] == 2000 + 1000 + 5000 + 6000 + 3000
    assert budget["within_cap"] is True
    assert estimate_budget(8000, None, 10_000)["within_cap"] is False
