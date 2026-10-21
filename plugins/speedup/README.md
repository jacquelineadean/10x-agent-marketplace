# speedup

Continuous performance optimization from your monitoring data. The plugin measures the
user journeys that matter at p75 from Datadog, Prometheus or imported files, ranks where
people wait longest against targets, guards every win with a deterministic benchmark whose
CI ceiling only moves down, and quantifies each change in the field. A dashboard shows it
all; an optional blog-style write-up tells the story with every number filled in from data.

The method follows "How we made claude.ai 3x faster in two weeks" (claude.dev, September
2026): pick journeys from usage data, gate code on stable proxies such as instruction
counts, ratchet those proxies in CI, ship behind flags in stages, and report p75 speedups
as a geometric mean across journeys.

Read-only against every data source. Standard-library Python. Data stays on your machine
until you choose to publish the dashboard as a private claude.ai Artifact.

## Install
```
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install speedup@10x-agent-marketplace
```
Needs Python 3.11+ or `uv`. No Python packages are downloaded.

## The loop
| Step | Command | Who does the work | Output |
| --- | --- | --- | --- |
| Set up | `/speedup:setup` | you choose journeys with Claude; `perf-gatherer` lists candidates | `perf/speedup.json`, CI workflow |
| Measure | `/speedup:measure` | `measure` or `perf-gatherer` + `import`, then `report` | history, regressions with suspects |
| Optimize | `/speedup:optimize [journey]` | Claude profiles, builds a proxy, changes code; a person approves | benchmark, ceiling, change log entry |
| Report | `/speedup:report [--writeup]` | `report`; `perf-writer` for the post; `writeup` fills numbers | private Artifact dashboard, `writeup.md` |

Run `measure` daily (a cloud routine, `/loop 1d /speedup:measure`, or CI) and the loop
is continuous: regressions surface within one window, and the priority list always names
the next journey to work on.

## Sources and credentials
| Source | `source.kind` | Credentials | Calls |
| --- | --- | --- | --- |
| Datadog metrics (APM, custom timings) | `datadog-metric` | `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE` | `GET /api/v1/query` |
| Datadog RUM | `datadog-rum` | same | `POST /api/v2/rum/analytics/aggregate` (a read-only query) |
| Prometheus | `prometheus` | `PROMETHEUS_URL`, optional `PROMETHEUS_TOKEN` | `GET /api/v1/query_range` (step 1 day; write the query over a `[1d]` range, read at the midnight that ends each day) |
| Datadog connector in Claude, other tools, exports | `file` or any kind | none in speedup | `import` of JSON or CSV |

- Datadog: an API key plus an application key with read access. Scope the application key
  to `timeseries_query` for metric journeys; RUM journeys need a key whose owner can read
  RUM data. `DD_SITE` is `datadoghq.com` (default), `us3.datadoghq.com`,
  `us5.datadoghq.com`, `datadoghq.eu`, `ap1.datadoghq.com`, `ap2.datadoghq.com` or
  `ddog-gov.com`. Keys are only sent to these hosts.
- The transport sends GET, plus POST only to the RUM aggregation path; any other POST is
  refused before a request is made. Keys never appear in logs or files.
- Prometheus uses https, or plain http on localhost without a token.
- With no keys, the `perf-gatherer` subagent reads the Datadog connector in Claude and
  writes import files. The connector must be authorized in claude.ai connector settings.
- `.env` in the working directory is read; it never overrides a set variable.

## Project file: `perf/speedup.json`
Committed to your repository. `init` writes a starter; `examples/demo/perf/speedup.json` is a
full example with nine journeys and six benchmarks.

| Key | Default | Meaning |
| --- | --- | --- |
| `project` | | name; the data folder is `~/speedup-runs/<project>/` |
| `percentile` | `p75` | the percentile your queries return, used in labels |
| `window_days` | 7 | current and previous windows |
| `impact_days` | 7 | days before and after a ship day for a change's field effect |
| `regression_threshold_pct` | 5 | slowdown against the previous window that counts as a regression (with p < 0.05) |
| `baseline` | first window of data | `{"since", "until"}` before optimization starts |
| `sources.datadog.site`, `sources.prometheus.url` | | overridden by `DD_SITE`, `PROMETHEUS_URL` |
| `journeys[]` | | `id`, `name`, `unit`, `direction` (`lower` or `higher`), `target`, `weight`, `source` |
| `journeys[].source` | `file` | `kind`, `query`, `measure` (RUM attribute), `aggregation` (`pc75`...), `scale` (to the journey unit) |
| `benchmarks[]` | | `id`, `name`, `command` (argument list, no shell), `parse`, `pattern`, `unit`, `repeat` (3), `journeys`, `ceiling`, `original`, `tolerance_pct` (1), `headroom_pct` (0.5), `max_cv_pct` (2), `timeout_s` (600) |

`parse` reads the number from the command's output: `number` (last number on stdout),
`valgrind` (`I refs` or `Collected`), `json` (`pattern` is a dotted key) or `regex`
(`pattern` with one capture group).

`perf/changes.jsonl` holds one change per line, written by `log`: id, title, journeys,
shipped date, pull request link, flag, rollout stage (`dev`, `employees`, `1%` to `100%`,
`rolled-back`), whether the flag is removed, and the proxy benchmark before and after.

## Commands
Run through `${CLAUDE_PLUGIN_ROOT}/scripts/speedup` in Claude Code, or without Claude:
`PYTHONPATH=plugins/speedup/src python3 -m speedup <command>`.
Global flags: `--config PATH` (default `perf/speedup.json` or `SPEEDUP_CONFIG`),
`--data DIR` (default `~/speedup-runs/<project>` or `SPEEDUP_RUNS`).

| Command | Does | Exit codes |
| --- | --- | --- |
| `init [--project NAME] [--force]` | starter project file and empty change log | 0, 1 |
| `measure [--days 28 \| --since D --until D] [--journey ID]` | fetch daily values, merge into history; ends yesterday | 0, 1 |
| `import FILE... [--journey ID]` | add daily values (JSON or CSV) or benchmark runs (JSON from `bench`) | 0, 1 |
| `bench [--benchmark ID] [--repeat N] [--values FILE] [--day D] [--commit SHA]` | run benchmarks, record medians and noise | 0, 1 |
| `guard [--benchmark ID] [--values FILE] [--strict]` | fail when a median is over ceiling plus tolerance | 0 pass, 2 over ceiling |
| `tighten [--benchmark ID] [--values FILE] [--dry-run]` | lower ceilings to median plus headroom; never raise; noisy runs never move one | 0, 1 |
| `log --title T [--journey ID] [--shipped D] [--pr URL] [--flag F] [--stage S] [--benchmark ID --before N --after N] [--notes]` | add a change; with `--id c-0001`, update one; reaching `100%` without a ship day ships it today | 0, 1 |
| `report [--max-tokens 25000]` | metrics, digest, dashboard, budget | 0, 2 over the token cap |
| `writeup` | fill `writeup.src.md` tokens into `writeup.md`, re-render the dashboard | 0, 2 unknown keys or hand-typed numbers |

Every command prints at most 15 lines; errors print one `error:` line and exit 1.

Import formats:
```json
{"journey": "fresh-load", "source": "Datadog MCP: RUM pc75 ...", "scale": 1e-6,
 "points": [{"date": "2026-10-01", "value": 812400000}]}
```
A JSON list of such objects works too, and CSV with a `date,value[,journey]` header.

## How the numbers are made
- A day's value is the median of that day's points from the source (sources return p75 per
  hour or per day). A window's value is the median of its days.
- Speedup is baseline over current for lower-is-better journeys and current over baseline
  for higher-is-better ones; above 1 is always better. The headline is the geometric mean
  of journey speedups, so a 4x win and a 2x loss do not average to 1x.
- Regressions and change effects use the Mann-Whitney rank test on daily values (normal
  approximation with tie correction). A change's field effect compares `impact_days` before
  and after its ship day, skipping the ship day, and needs 3 days on each side. Changes on
  the same journey within that span are listed as overlapping; their effects are shared.
- Priority score is the gap to target in percent times the journey weight; regressions sort
  first.

## Data folder
Default `~/speedup-runs/<project>/`. Never commit it.

| File | Written by | Claude reads it? |
| --- | --- | --- |
| `history.json` | `measure`, `import`: daily value per journey | never |
| `bench.json` | `bench`, `import`: benchmark runs | never |
| `raw/*.json` | `measure`: source responses for audit | never |
| `metrics.json` | `report`, `schema_version` 1 | never in full |
| `digest.md` | `report`, at most 12,000 bytes, every number with its key | yes |
| `budget.json` | `report`: token estimate against `--max-tokens` | no |
| `dashboard.html` | `report`, `writeup`: full document, opens from disk | no |
| `artifact.html` | `report`, `writeup`: the same page as an Artifact body | published |
| `writeup.src.md` | `perf-writer`, with `{{key}}` tokens | written |
| `writeup.md` | `writeup`: numbers filled, sources table appended | the user's |

### metrics.json shape (schema_version 1)
Top-level keys: `schema_version`, `generated_at`, `project`, `percentile`, `as_of`,
`windows` (baseline, current, previous), `headline`, `journeys`, `priorities`, `changes`,
`benchmarks`, `rollout`, `limits`, `warnings`.

- `headline`: journeys, journeys_measured, journeys_with_target, journeys_at_target,
  journeys_regressed, geomean_speedup, best_journey, best_speedup, changes,
  changes_shipped, changes_at_full_rollout, changes_rolled_back, changes_improved,
  flags_added, flags_removed, flags_open, guardrails, guardrails_with_ceiling,
  median_ceiling_reduction_pct.
- `journeys.<id>`: name, unit, direction, percentile, target, weight, source,
  days_with_data, series, coverage_pct, baseline, current, previous, best_day, speedup,
  improvement_pct, vs_baseline_p, vs_previous_pct, vs_previous_p, gap_to_target_pct,
  at_target, regressed, status (`at-target`, `improving`, `flat`, `slower`, `regressed`,
  `measuring`, `stale`, `no-data`).
- `changes[]`: id, title, journeys, shipped, pr, flag, stage, flag_removed, notes,
  overlaps, `impact[]` (journey, unit, before, after, improvement_pct, speedup, p,
  days_before, days_after, verdict), `proxy` (benchmark, unit, before, after,
  reduction_pct).
- `benchmarks.<id>`: name, unit, journeys, command, original, ceiling, tolerance_pct, runs,
  history, ceiling_reduction_pct, latest, latest_date, latest_cv_pct, noisy,
  latest_reduction_pct, within_ceiling.

Write-up tokens are dotted keys into this shape. Change rows are addressed by id and impact
rows by journey: `{{changes.c-0002.impact.conversation-switch.improvement_pct}}`.

## Dashboard
One page, no scripts: a summary band (overall speedup, journeys at target, changes shipped
and won, regressions, ceiling cut, open flags), speedup bars on a log scale, one chart per
journey (daily values, target, baseline and current windows, ship marks), the priority
table, the change ledger with field effect, proxy and rollout, guardrail cards with each
ceiling's ratchet, the write-up when present, and method notes with every source query.
Light and dark themes; one column on phones. Fonts load from Google Fonts with local
fallbacks, so the file also opens offline.

## Token budget
`budget.json` sums the digest (at most 3,000 tokens), the outline plus writer instructions,
system overhead 5,000, output allowance 6,000 and main conversation 3,000. Over
`--max-tokens` (default 25,000) `report` exits 2 and the skill asks before writing.

## Limits
- Field data moves with traffic mix, devices and releases outside the change log. The rank
  test shows a shift around a ship day; it does not prove the change caused it.
- A metric query that returns several series uses the first and warns; aggregate across
  groups in the query.
- Daily resolution: effects smaller than day-to-day noise read as "no clear effect".
- Benchmarks run your commands on your machine or CI; speedup adds no sandbox.

## Demo
Invented data for a made-up chat app, Lumen, shaped like a two-week sprint with a later
regression:
```
S=/tmp/perf-demo
plugins/speedup/scripts/speedup --config plugins/speedup/examples/demo/perf/speedup.json --data $S import plugins/speedup/examples/demo/imports/*.json
plugins/speedup/scripts/speedup --config plugins/speedup/examples/demo/perf/speedup.json --data $S report
cp plugins/speedup/examples/demo/writeup.src.md $S/ && plugins/speedup/scripts/speedup --config plugins/speedup/examples/demo/perf/speedup.json --data $S writeup
```
Then open `$S/dashboard.html`. `examples/demo/generate.py` rebuilds the imports.

## Manual test
1. Set `DD_API_KEY`, `DD_APP_KEY` and `DD_SITE` for a Datadog org with RUM or APM data.
2. In a scratch folder: `speedup init --project trial`, then edit one journey's query
   to a real RUM view or APM service.
3. `speedup measure --days 14`: expect one line per journey with a day count, and
   `raw/` files in `~/speedup-runs/trial/`.
4. `speedup report`: expect at most 15 lines and five files; open `dashboard.html`.
5. Without keys, in Claude Code with the Datadog connector authorized:
   `/speedup:measure` runs `perf-gatherer` and `import` instead.
6. `/speedup:report --writeup`: expect `writeup.md` with a sources table and a
   published private Artifact.
7. Add a benchmark, run `bench`, `tighten`, then `guard` with a `--values` file 5% above
   the ceiling: expect exit 2.

## Development
```
uv sync
uv run pytest plugins/speedup/tests
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/speedup/src/speedup
claude plugin validate .
```
Tests use recorded Datadog and Prometheus responses under `tests/fixtures/`; no test calls a
live API.
