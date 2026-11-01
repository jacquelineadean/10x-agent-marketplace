"""`briefing refresh` and the Google and Microsoft upload manifests.

Refresh runs in its own process against a stand-in `psql` on PATH, so the collector's real
argument list, environment and standard input are exercised without a database.
"""

from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

import pytest
from briefing.core import upload
from briefing_helpers import run

FAKE_PSQL = """#!/usr/bin/env python3
import json, os, sys
script = sys.stdin.read()
assert "default_transaction_read_only=on" in os.environ["PGOPTIONS"]
assert "--set" in sys.argv and "start=" in " ".join(sys.argv)
if "count(*)" in script:
    print(json.dumps([{"count": 2565}]))
else:
    print(json.dumps([
        {"month": "2026-08", "orders": 905},
        {"month": "2026-09", "orders": 875},
        {"month": "2026-10", "orders": 932},
    ]))
"""

STORY = {
    "layout": "dashboard",
    "meta": {"title": "Shop orders", "kicker": "Ops", "as_of": "2026-10-14"},
    "sources": [
        {"id": "postgres", "label": "Orders database", "as_of": "2026-10-14"},
        {"id": "github", "label": "GitHub", "as_of": "2026-10-14"},
    ],
    "chapters": [
        {
            "id": "orders",
            "title": "Orders",
            "blocks": [
                {
                    "type": "kpi",
                    "items": [
                        {
                            "label": "Paid orders",
                            "value": "@postgres.paid",
                            "target": 2000,
                            "better": "up",
                        },
                        {
                            "label": "Merged PRs",
                            "value": "@github.merged",
                            "target": 300,
                            "better": "up",
                        },
                    ],
                },
                {
                    "type": "chart",
                    "chart": "bars",
                    "title": "Orders per month",
                    "source": "postgres",
                    "data": {
                        "categories": "@postgres.orders.month",
                        "series": [{"name": "Orders", "values": "@postgres.orders.orders"}],
                    },
                },
            ],
        }
    ],
}


def _folder(tmp_path: Path) -> Path:
    run_folder = tmp_path / "run"
    run_folder.mkdir()
    window = {"start": "2026-07-01", "end": "2026-09-30"}
    facts = {
        "postgres": {
            "paid": {"value": 2685, "source": "postgres"},
            "orders": {"month": ["2026-07", "2026-08", "2026-09"], "orders": [905, 905, 875]},
        },
        "github": {"merged": {"value": 412, "source": "github"}},
    }
    queries = {
        "schema_version": 1,
        "queries": {
            "postgres.paid": {
                "system": "postgres",
                "lane": "script",
                "connection": "postgres",
                "request": {"sql": "SELECT count(*) FROM orders WHERE day BETWEEN :start AND :end"},
                "query": "SELECT count(*) FROM orders",
                "window": window,
                "as_of": "2026-10-14",
            },
            "postgres.orders": {
                "system": "postgres",
                "lane": "script",
                "connection": "postgres",
                "request": {"sql": "SELECT month, orders FROM monthly WHERE day >= :start"},
                "query": "SELECT month, orders FROM monthly",
                "window": window,
                "as_of": "2026-10-14",
            },
            "github.merged": {
                "system": "github",
                "lane": "mcp",
                "connection": "github",
                "query": 'search_issues q="is:pr is:merged"',
                "window": window,
                "as_of": "2026-10-14",
            },
        },
    }
    (run_folder / "story.json").write_text(json.dumps(STORY))
    (run_folder / "facts.json").write_text(json.dumps(facts))
    (run_folder / "queries.json").write_text(json.dumps(queries))
    return run_folder


def test_refresh_reads_script_queries_again_and_marks_connector_facts_stale(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    psql = bin_dir / "psql"
    psql.write_text(FAKE_PSQL)
    psql.chmod(0o755)
    env = {
        "PATH": f"{bin_dir}:/usr/bin:/bin",
        "DATABASE_URL": "postgresql://reader:pw@db/shop",
        "SOURCES_CONNECTIONS": str(tmp_path / "none.json"),
    }
    result = run("refresh", str(folder / "story.json"), "--until", "2026-11-01", env=env)
    assert result.returncode == 0, result.stderr
    assert "postgres.orders: 3 rows x 2 columns, 2026-08-01..2026-10-31, as of 2026-11-01" in (
        result.stdout
    )
    facts = json.loads((folder / "facts.json").read_text())
    assert facts["postgres"]["orders"]["month"] == ["2026-08", "2026-09", "2026-10"]
    assert facts["postgres"]["paid"]["value"] == 2565
    assert facts["github"]["merged"]["value"] == 412
    plan = json.loads((folder / "queries.json").read_text())
    assert plan["refreshed"] == "2026-11-01"
    page = (folder / "build" / "index.html").read_text()
    assert '<p class="db-asof">As of 1 Nov 2026</p>' in page
    assert '<p class="db-stale">Not refreshed: GitHub as of 14 Oct 2026</p>' in page
    assert page.count('class="kpi-stale"') == 1
    assert "Not refreshed since 14 Oct 2026" in page
    assert 'data-asof="2026-10-14" data-stale="1"' in page
    assert 'data-asof="2026-11-01">2,565<' in page


def test_refresh_needs_a_queries_file(tmp_path: Path) -> None:
    folder = tmp_path / "bare"
    folder.mkdir()
    (folder / "story.json").write_text(json.dumps(STORY))
    result = run("refresh", str(folder / "story.json"))
    assert result.returncode == 1 and "gather facts first" in result.stderr


def _pptx(slides: int) -> bytes:
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as deck:
        deck.writestr("ppt/presentation.xml", "<p:presentation/>")
        for n in range(1, slides + 1):
            deck.writestr(f"ppt/slides/slide{n}.xml", "<p:sld/>")
    return data.getvalue()


def test_the_upload_manifest_asks_before_google_converts_a_pptx() -> None:
    data = _pptx(7)
    found = upload.manifest("google", Path("q4.pptx"), data, STORY)
    assert found["confirm"] == (
        'Upload "Shop orders.pptx" (7 slides, 1 KB) to Google Drive as Google Slides? '
        "It shows numbers from Orders database and GitHub."
    )
    assert found["convert_to"] == upload.GOOGLE_SLIDES
    assert found["mime_type"] == upload.PPTX and found["slides"] == 7
    pdf = (
        b"%PDF-1.7\n1 0 obj << /Type /Pages >>\n2 0 obj << /Type /Page >>\n3 0 obj << /Type/Page >>"
    )
    printed = upload.manifest("microsoft", Path("deck.pdf"), pdf, STORY)
    assert printed["slides"] == 2 and "convert_to" not in printed
    assert printed["service"] == "Microsoft 365 (OneDrive or SharePoint)"


def test_an_upload_refuses_files_that_are_not_decks() -> None:
    with pytest.raises(upload.UploadError, match="not a PowerPoint"):
        upload.manifest("google", Path("x.pptx"), b"hello", STORY)
    with pytest.raises(upload.UploadError, match=r"\.pptx or \.pdf"):
        upload.manifest("google", Path("x.key"), b"", STORY)
    with pytest.raises(upload.UploadError, match="not a PDF"):
        upload.manifest("microsoft", Path("x.pdf"), b"PK", STORY)


def test_export_to_google_writes_the_manifest_and_needs_a_file(tmp_path: Path) -> None:
    folder = _folder(tmp_path)
    deck = tmp_path / "Shop orders.pptx"
    deck.write_bytes(_pptx(3))
    made = run("export", str(folder / "story.json"), "--to", "google", "--file", str(deck))
    assert made.returncode == 0, made.stderr
    data = json.loads((folder / "build" / "upload.json").read_text())
    assert data["file"] == str(deck.resolve()) and data["slides"] == 3
    assert made.stdout.splitlines()[1].startswith('ask first: Upload "Shop orders.pptx"')
    missing = run("export", str(folder / "story.json"), "--to", "microsoft")
    assert missing.returncode == 1 and "needs --file" in missing.stderr
