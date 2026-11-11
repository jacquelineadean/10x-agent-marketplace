"""The solutions block: formulas, the solutions file, the simulator, the digest, the
decision, the command line and the page's script against the build's numbers."""

from __future__ import annotations

import copy
import json
import re
import shutil
from pathlib import Path
from typing import Any

import pytest
from blueprint.core.solutions import decision, digest, formula, simulate
from blueprint.core.solutions import spec as reader
from blueprint_helpers import EXAMPLES, PLUGIN, run
from chronicle_engine.connectors.browser import devtools, shoot
from chronicle_engine.core.story.model import Report

EXAMPLE = EXAMPLES / "catalog-solutions"
ASSETS = PLUGIN / "src" / "blueprint" / "assets"


def test_the_scout_runs_on_haiku_without_shell_or_edit_and_the_skill_names_its_parts() -> None:
    scout = (PLUGIN / "agents" / "solution-scout.md").read_text(encoding="utf-8")
    front = scout.split("---")[1]
    assert "\nname: solution-scout\n" in front and "\nmodel: haiku\n" in front
    assert "\ntools: Read, Grep, Glob, Write\n" in front
    skill = PLUGIN / "skills" / "solution-visualizer"
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert "\nname: solution-visualizer\n" in text.split("---")[1]
    assert "blueprint:solution-scout" in text and len(text.splitlines()) < 100
    for reference in re.findall(r"`(references/[a-z-]+\.md)`", text):
        assert (skill / reference).is_file(), reference
    assert "references/solutions-format.md" in text and "references/implement.md" in text


def _raw() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLE / "solutions.json").read_text(encoding="utf-8"))
    return data


def _facts() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLE / "facts.json").read_text(encoding="utf-8"))
    return data


def _run(raw: dict[str, Any] | None = None) -> tuple[simulate.Run | None, Report]:
    report = Report()
    return simulate.run(json.dumps(raw or _raw()), _facts(), report), report


def _example() -> simulate.Run:
    found, report = _run()
    assert found is not None, report.errors
    return found


@pytest.mark.parametrize(
    ("text", "values", "result"),
    [
        ("2 + 3 * 4", {}, 14.0),
        ("a / b if b > 0 else 0", {"a": 6.0, "b": 0.0}, 0.0),
        ("a / b if b > 0 else 0", {"a": 6.0, "b": 4.0}, 1.5),
        ("min(a, 3) ** 2", {"a": 5.0}, 9.0),
        ("clamp(a, 0, 100)", {"a": 250.0}, 100.0),
        ("round(a)", {"a": 2.5}, 3.0),
        ("round(a)", {"a": -2.5}, -2.0),
        ("a % 3", {"a": -1.0}, 2.0),
        ("not a or (a and 0)", {"a": 0.0}, 1.0),
        ("b > 0 and a / b > 1", {"a": 1.0, "b": 0.0}, 0.0),
    ],
)
def test_a_formula_computes_by_the_rules_the_page_shares(
    text: str, values: dict[str, float], result: float
) -> None:
    assert formula.evaluate(formula.parse(text), values) == result


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("__import__('os')", "unknown function"),
        ("a.b", "is not arithmetic"),
        ("[a for a in b]", "is not arithmetic"),
        ("'text'", "is not a number"),
        ("sqrt(1, 2)", "takes 1 argument"),
        ("1 < a < 3", "is not arithmetic"),
        ("a +", "cannot read"),
    ],
)
def test_a_formula_that_is_not_arithmetic_is_refused(text: str, message: str) -> None:
    with pytest.raises(formula.FormulaError, match=message):
        formula.parse(text)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("1 / a", "division by zero"),
        ("log(a)", "log of 0"),
        ("b", "unknown name 'b'"),
        ("exp(1000)", "not a real number"),
        ("1e308 * 10", "too large"),
    ],
)
def test_a_value_that_is_not_finite_raises(text: str, message: str) -> None:
    with pytest.raises(formula.FormulaError, match=message):
        formula.evaluate(formula.parse(text), {"a": 0.0})


def test_the_page_script_has_every_operation_the_reader_emits() -> None:
    script = (ASSETS / "js" / "84-solutions-model.js").read_text(encoding="utf-8")
    table = script[script.index("var SOL_OPS = {") : script.index("function solEval")]
    in_page = set(re.findall(r"^    ([a-z]+): function", table, re.MULTILINE))
    lazy = {"if", "and", "or"}
    emitted = {*formula.BINARY.values(), *formula.COMPARE.values(), *formula.FUNCTIONS}
    assert in_page | lazy == emitted | {"neg", "not"} | lazy
    assert all(f'op === "{name}"' in script for name in lazy)


def test_the_example_computes_what_its_formulas_say() -> None:
    found = _example()
    typical = found.results["typical"]
    assert typical["direct"]["p95_ms"] == pytest.approx(40 * (1 + 3 * 0.8**2))
    assert typical["cache"]["stale_s"] == 60
    assert typical["view"]["cost"] == 1400 + 2 * 90 + 300
    assert found.results["sale"]["direct"]["errors"] == pytest.approx(100 * (1 - 1 / 4.8))
    assert found.results["reprice"]["view"]["stale_s"] == pytest.approx(0.5 / 0.00014)


def test_a_setting_turned_off_takes_its_off_value() -> None:
    spec = _example().spec
    direct = spec["approaches"][0]
    given = {**simulate.inputs_of(spec, spec["scenarios"][2])}
    on = simulate.measure(direct, {**given, **simulate.settings_for(spec, direct)})
    off = simulate.measure(
        direct, {**given, **simulate.settings_for(spec, direct, off=frozenset({"timeout_ms"}))}
    )
    assert on["p95_ms"] == 250 and on["errors"] > 60
    assert off["p95_ms"] == pytest.approx(220 * (1 + 3 * 0.8**2)) and off["errors"] == 0


def test_an_approach_reads_only_its_own_settings_and_shared_formulas() -> None:
    spec = _example().spec
    assert [s["id"] for s in reader.settings_of(spec, "view")] == ["consumers", "store_ms"]
    assert [name for name, _ in spec["approaches"][0]["steps"]] == [
        "util",
        "raw_ms",
        "capped_ms",
        "late_pct",
        "shed_pct",
    ]
    assert spec["approaches"][2]["steps"][0][0] == "busy"


def _changed(path: list[Any], value: Any) -> dict[str, Any]:
    raw = _raw()
    node: Any = raw
    for key in path[:-1]:
        node = node[key]
    if value is None:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return raw


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (["approaches", 0, "measures", "p95_ms"], "capped_ms + ttl_s", "'ttl_s' is not an input"),
        (["approaches", 0, "let", "util"], "util + 1", "util -> util is a circle"),
        (["approaches", 0, "measures", "cost"], None, "missing a formula for 'cost'"),
        (["approaches", 0, "measures", "p95_ms"], "rps / (replicas - 2)", "division by zero"),
        (["approaches", 0, "measures", "cost"], "1 / (rps - 3000)", "with rps at 3000"),
        (["approaches", 0, "id"], "min", "not a formula word"),
        (["approaches"], _raw()["approaches"][:1], "needs 2 to 6 approaches"),
        (["inputs", 0, "value"], 10, "min below max and value between them"),
        (["inputs", 0, "value"], "@traffic.nothing", "no fact 'traffic.nothing'"),
        (["inputs", 1, "id"], "rps", "'rps' is used twice"),
        (["settings", 0, "approaches"], ["direct", "nowhere"], "names no approach 'nowhere'"),
        (["settings", 3, "off"], 0, "off must be a number, on a number or a choice"),
        (["settings", 5, "value"], 4, "must be the value of one of its options"),
        (["scenarios", 1, "inputs"], {"rps": 9000}, "is not a value 'Page views per second'"),
        (["scenarios", 1, "inputs"], {"speed": 1}, "names no control here"),
        (["measures", 0, "feel"], "failures", "feel failures reads a unit of %"),
        (["measures", 0, "better"], "faster", "better must be lower or higher"),
    ],
)
def test_a_solutions_file_error_says_what_to_change(
    path: list[Any], value: Any, message: str
) -> None:
    found, report = _run(_changed(path, value))
    assert found is None
    assert any(message in error for error in report.errors), report.errors


def test_a_control_that_moves_nothing_and_a_typed_number_are_warnings() -> None:
    raw = _raw()
    raw["inputs"].append({"id": "idle", "label": "Top 10 products", "value": 1, "min": 0, "max": 5})
    found, report = _run(raw)
    assert found is not None
    assert "solutions: idle changes no measure from its min to its max" in report.warnings
    assert any("number '10' has no fact token" in w for w in report.warnings)
    assert _run()[1].warnings == []


def test_the_digest_gives_results_misses_swings_and_assumptions_under_the_cap() -> None:
    found = _example()
    text = digest.digest(found, "solutions")
    assert len(text.encode("utf-8")) < digest.DIGEST_CAP
    assert "| Query the database (`direct`) | 250 ms (missed) | 79.2% (missed) |" in text
    assert "- Read a view kept by events misses Oldest price shown in Catalog reprice" in text
    assert "(`swr`) off to on | 60 s | 120 s |" in text
    assert "- Reads one replica serves (`replica_rps`): 250 rps" in text
    big = copy.deepcopy(found)
    big.spec["scenarios"] = found.spec["scenarios"] * 12
    cut = digest.digest(big, "solutions")
    assert len(cut.encode("utf-8")) <= digest.DIGEST_CAP and "Cut at 12 KB" in cut


def test_the_examples_stored_results_and_digest_are_current() -> None:
    found = _example()
    stored = json.loads((EXAMPLE / "solutions-results.json").read_text(encoding="utf-8"))
    assert not digest.stale(stored["solutions"], found)
    assert (EXAMPLE / "solutions-digest.md").read_text(encoding="utf-8") == digest.digest(
        found, "solutions"
    )
    stored["solutions"]["sale"]["cache"]["p95_ms"]["value"] += 1
    assert digest.stale(stored["solutions"], found)


def _decision() -> dict[str, Any]:
    data: dict[str, Any] = json.loads((EXAMPLE / "decision.json").read_text(encoding="utf-8"))
    return data


def test_a_decision_becomes_settings_expectations_and_checks() -> None:
    spec = _example().spec
    report = Report()
    chosen = decision.read(spec, _decision(), report)
    assert chosen is not None, report.errors
    text = decision.brief(spec, chosen)
    assert "Chosen: **Cache, two-minute lifetime** (approach `cache`)" in text
    assert (
        "| Cache lifetime (`ttl_s`) | 120 s (changed) | 60 s | `CATALOG_CACHE_TTL_SECONDS` |"
        in text
    )
    assert "| Database degraded (`slow_db`) | 188 ms (met) |" in text
    assert "| Launch day (`saved_1`) | 45 ms (met) |" in text
    assert text.count("- [ ] ") == 5 * 3 and "outside their budget" not in text
    assert "| Read a view kept by events (`view`) | 5 ms (met) |" in text
    assert "- Reads one replica serves (`replica_rps`): 250 rps" in text


def test_a_decision_with_a_setting_off_and_new_inputs_reports_the_misses() -> None:
    spec = _example().spec
    raw = _decision()
    raw["chosen"] = "cache"
    raw["variants"][0].update(off=["timeout_ms"], settings={"ttl_s": 600, "swr": 1})
    raw["inputs"]["rps"] = 2800
    chosen = decision.read(spec, raw, Report())
    assert chosen is not None
    text = decision.brief(spec, chosen)
    assert "| Database timeout (`timeout_ms`) | turned off (0 ms) (changed) | 250 ms |" in text
    assert "| Inputs when decided (`decided`) |" in text
    assert "The model gives 1,200 s, outside the budget." in text
    assert "The model puts 6 of 18 checks outside their budget." in text


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"chosen": "nobody"}, "decision.chosen 'nobody' names no variant"),
        ({"inputs": {"rps": 99999}}, "decision.inputs.rps is not a value"),
        ({"variants": [{"id": "x", "approach": "mainframe"}]}, "names no approach"),
        (
            {"variants": [{"id": "cache_9", "approach": "cache", "settings": {"consumers": 2}}]},
            "settings.consumers names no control here",
        ),
        (
            {"variants": [{"id": "cache_9", "approach": "cache", "off": ["ttl_s"]}]},
            "off 'ttl_s' is not a setting that turns off",
        ),
    ],
)
def test_a_decision_the_file_cannot_hold_is_refused(change: dict[str, Any], message: str) -> None:
    report = Report()
    assert decision.read(_example().spec, {**_decision(), **change}, report) is None
    assert any(message in error for error in report.errors), report.errors


def _copy(tmp: Path) -> Path:
    folder = tmp / "catalog-solutions"
    shutil.copytree(EXAMPLE, folder, ignore=shutil.ignore_patterns("build"))
    return folder / "story.json"


def test_the_example_checks_clean_and_builds_the_page(tmp_path: Path) -> None:
    story = _copy(tmp_path)
    checked = run("check", str(story))
    assert checked.returncode == 0 and "0 warning(s)" in checked.stdout, checked.stderr
    built = run("build", str(story))
    assert built.returncode == 0, built.stderr
    page = (story.parent / "build" / "index.html").read_text(encoding="utf-8")
    assert 'class="fig solutions wide"' in page and "INIT.solutions = initSolutions" in page
    assert '"expect":{"typical":{"direct":{"p95_ms":116.8' in page
    assert '<th scope="row">Read through a cache</th><td>45 ms</td>' in page
    assert 'class="proto-cell span-2"' in page
    assert "The replicas run out" in page and ">79.2%</span>" in page


def test_results_older_than_the_file_stop_the_build(tmp_path: Path) -> None:
    story = _copy(tmp_path)
    path = story.parent / "solutions.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["settings"][2]["value"] = 90
    path.write_text(json.dumps(data), encoding="utf-8")
    stale = run("check", str(story))
    assert stale.returncode == 1
    assert "the results under 'solutions' are older than solutions.json" in stale.stderr
    (story.parent / "solutions-results.json").unlink()
    again = run("solutions", "simulate", str(story))
    assert again.returncode == 0 and "6 budget miss(es)" in again.stdout, again.stderr
    assert run("check", str(story)).returncode == 0


def test_a_second_solutions_block_is_an_error(tmp_path: Path) -> None:
    story = _copy(tmp_path)
    data = json.loads(story.read_text(encoding="utf-8"))
    data["chapters"][1]["blocks"].append({"type": "solutions", "file": "solutions.json"})
    story.write_text(json.dumps(data), encoding="utf-8")
    result = run("check", str(story))
    assert result.returncode == 1 and "a story holds one solutions block" in result.stderr


def test_new_starts_a_run_that_builds(tmp_path: Path) -> None:
    folder = tmp_path / "reads"
    made = run("solutions", "new", str(folder), "--title", "Reads")
    assert made.returncode == 0, made.stderr
    assert "0 budget miss(es)" in made.stdout and "next: write solutions.json" in made.stdout
    assert json.loads((folder / "story.json").read_text(encoding="utf-8"))["layout"] == "prototype"
    assert "| First approach (`first`) | 123 ms (met) |" in (
        folder / "solutions-digest.md"
    ).read_text(encoding="utf-8")
    assert run("build", str(folder / "story.json")).returncode == 0
    assert run("solutions", "new", str(folder)).returncode == 1


def test_decide_writes_decision_md_and_refuses_a_bad_export(tmp_path: Path) -> None:
    story = _copy(tmp_path)
    export = story.parent / "decision.json"
    made = run("solutions", "decide", str(story), "--decision", str(export))
    assert made.returncode == 0, made.stderr
    assert "Cache, two-minute lifetime" in made.stdout
    assert "## Settings to implement" in export.with_suffix(".md").read_text(encoding="utf-8")
    bad = _decision()
    bad["variants"][1]["settings"]["ttl_s"] = 5000
    export.write_text(json.dumps(bad), encoding="utf-8")
    refused = run("solutions", "decide", str(story), "--decision", str(export))
    assert refused.returncode == 1
    assert "settings.ttl_s is not a value 'Cache lifetime' can hold" in refused.stderr


# Moves the first input, turns a setting off, adds a variant and chooses it; then reads
# what the page shows and what it would export.
DRIVE = """
(() => {
  const q = (s, n) => Array.from((n || document).querySelectorAll(s));
  const values = card => q('.sol-m dd b', card).map(n => n.textContent);
  const out = {drift: q('.sol-drift').length, start: q('.sol-card').map(values)};
  q('.sol-chip').find(b => b.textContent === 'Database degraded').click();
  const rps = q('.sol-side input[type=range]')[0];
  rps.value = '1000';
  rps.dispatchEvent(new Event('input', {bubbles: true}));
  const direct = q('.sol-card')[0];
  const on = q('.ctl .sol-check input', direct)[0];
  on.checked = false;
  on.dispatchEvent(new Event('change', {bubbles: true}));
  out.moved = values(q('.sol-card')[0]);
  q('.sol-card-foot button', q('.sol-card')[1])[0].click();
  out.cards = q('.sol-card').length;
  q('.sol-choose', q('.sol-card')[2])[0].click();
  q('.sol-copy')[0].click();
  out.decision = JSON.parse(q('.sol-json')[0].value);
  out.lanes = q('.sol-feel .sol-lane').length;
  return out;
})()
"""


def test_the_page_script_computes_the_builds_numbers(tmp_path: Path) -> None:
    try:
        browser = shoot.find()
    except shoot.BrowserError:
        pytest.skip("no Chromium on this machine")
    story = _copy(tmp_path)
    assert run("build", str(story)).returncode == 0
    with devtools.Capture(browser) as capture:
        capture.open((story.parent / "build" / "index.html").resolve().as_uri(), 1280, 900)
        seen = capture.evaluate(DRIVE)
    found = _example()
    spec = found.spec
    measures = spec["measures"]
    assert seen["drift"] == 0
    assert seen["start"] == [
        [digest.show(found.results["typical"][a["id"]][m["id"]], m) for m in measures]
        for a in spec["approaches"]
    ]
    direct = spec["approaches"][0]
    given = {**simulate.inputs_of(spec, spec["scenarios"][2]), "rps": 1000.0}
    off = simulate.settings_for(spec, direct, off=frozenset({"timeout_ms"}))
    wanted = simulate.measure(direct, {**given, **off})
    assert seen["moved"] == [digest.show(wanted[m["id"]], m) for m in measures]
    assert seen["cards"] == 4 and seen["lanes"] == 2 * 4
    exported = decision.read(spec, seen["decision"], Report())
    assert exported is not None
    assert exported["chosen"]["approach"] == "cache" and exported["inputs"]["rps"] == 1000
    assert exported["variants"][0]["off"] == ["timeout_ms"]


# One measure per operation, on values that separate the page's rules from JavaScript's own:
# a negative modulo, a half that rounds, a guarded division and lazy `and`.
OPERATIONS = {
    "arithmetic": "(load + 3) * 2 - load / 4",
    "modulo": "(0 - load) % 7",
    "power": "pow(load, 0.5) + load ** 2 / 1000",
    "rounding": "round(load / 40) + ceil(load / 7) + floor(load / 7)",
    "bounds": "min(load, 50, 70) + max(load, 500) + abs(0 - load) + clamp(load, 0, 60)",
    "curves": "sqrt(load) + log(load) + exp(load / 100)",
    "compare": "(load < 100) + (load <= 100) * 2 + (load > 100) * 4 + (load >= 100) * 8",
    "equal": "(load == 100) + (load != 100) * 2 + (not load) * 4",
    "logic": "(spare > 0 and load / spare > 1) + (spare == 0 or load / spare > 1) * 2",
    "guard": "load / spare if spare > 0 else 0 - 1",
}


def test_the_page_script_agrees_on_every_operation(tmp_path: Path) -> None:
    try:
        browser = shoot.find()
    except shoot.BrowserError:
        pytest.skip("no Chromium on this machine")
    folder = tmp_path / "operations"
    assert run("solutions", "new", str(folder)).returncode == 0
    path = folder / "solutions.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    raw["inputs"].append({"id": "spare", "label": "Spare", "value": 0, "min": 0, "max": 9})
    raw["scenarios"][1]["inputs"] = {"load": 730, "spare": 3}
    raw["measures"] = [{"id": name, "label": name, "decimals": 2} for name in OPERATIONS]
    for approach, workers in zip(raw["approaches"], ("workers", "workers * 2"), strict=True):
        approach["measures"] = {k: f"{v} + {workers}" for k, v in OPERATIONS.items()}
    path.write_text(json.dumps(raw), encoding="utf-8")
    story = folder / "story.json"
    assert run("solutions", "simulate", str(story)).returncode == 0
    built = run("build", str(story))
    assert built.returncode == 0, built.stderr
    with devtools.Capture(browser) as capture:
        capture.open((folder / "build" / "index.html").resolve().as_uri(), 1280, 900)
        seen = capture.evaluate(
            "(() => { const q = s => Array.from(document.querySelectorAll(s));"
            " q('.sol-chip')[1].click();"
            " return {drift: q('.sol-drift').map(n => n.textContent),"
            " first: q('.sol-card')[0].querySelectorAll('.sol-m dd b').length,"
            " shown: q('.sol-card:first-child .sol-m dd b').map(n => n.textContent)}; })()"
        )
    report = Report()
    found = simulate.run(json.dumps(raw), {}, report)
    assert found is not None, report.errors
    peak = found.results["peak"]["first"]
    assert peak["modulo"] == 5 + 4 and peak["logic"] == 1 + 2 + 4 and peak["equal"] == 2 + 4
    assert found.results["typical"]["first"]["guard"] == -1 + 4
    assert seen["drift"] == []
    assert seen["shown"] == [digest.show(peak[m["id"]], m) for m in found.spec["measures"]]
