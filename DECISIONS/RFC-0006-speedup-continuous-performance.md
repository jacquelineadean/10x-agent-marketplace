---
id: RFC-0006
title: speedup plugin: continuous performance optimization from monitoring data
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude project thread "Performance optimization plugin", 21 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0001, RFC-0002]
author: Claude Code, for Jacqueline Dean
created: 2026-10-21
---

# RFC-0006 — speedup plugin: continuous performance optimization from monitoring data

## 1. Summary
A new plugin, speedup 0.1.0, turns the method of "How we made claude.ai 3x faster in two
weeks" (claude.dev, September 2026) into a loop any team can run from its monitoring data:

1. **Journeys from field data.** A project file in the user's repository names 5 to 15 user
   journeys, each with a Datadog RUM, Datadog metric, Prometheus or file source, a p75
   target and a weight. `measure` fetches one value per day; `import` takes values gathered
   by the Datadog connector in Claude or exported from another tool.
2. **Numbers computed in code.** Speedup per journey and the geometric mean across journeys,
   gap to target, regressions against the previous window, and each change's field effect
   with a Mann-Whitney rank test.
3. **The ratchet.** Proxy benchmarks (instruction counts, React commits, DOM mutations) run
   as argument-list commands. `guard` fails CI over a ceiling; `tighten` lowers ceilings and
   never raises one.
4. **A change log.** `perf/changes.jsonl` records each optimization with its flag, rollout
   stage and proxy numbers, so the dashboard can show effects and name regression suspects.
5. **Outputs.** A script-free dashboard published as a private claude.ai Artifact, and an
   optional blog-style write-up whose numbers are tokens filled from `metrics.json`.

Four skills drive it: `setup`, `measure`, `optimize`, `report`. Two subagents keep raw tool
output and long prose out of the main conversation: `perf-gatherer` and `perf-writer`.

## 2. The need
**User scenario:** the request asked for a performance optimization plugin inspired by
the claude.ai post, using monitoring tools such as Datadog to optimize continuously, with a
dashboard that quantifies optimizations and an optional blog-style summary of every step.

The post itself was not reachable from the build environment (claude.dev is blocked by the
network policy). Its method comes from secondary coverage, checked across five sources:

| Claim from the post | Effect on this design |
| --- | --- |
| p75 time to a typeable page fell from 3.1 s to 0.55 s; 3.1x geometric mean over 13 measurements | journeys at a percentile; geometric mean headline |
| About 20 projects, each aimed at one user journey; Claude used Datadog data to pick them | journeys, weights, priority list; Datadog first |
| Wall-clock time was too noisy to gate on; instruction counts under valgrind, React commits and DOM mutations instead | proxy benchmarks, `parse: valgrind`, noise check |
| Benchmarks became CI guardrails; a daily job lowered ceilings when counts dropped | `guard`, `tighten`, the CI example |
| Flaky benchmarks or ones that did not track latency were thrown out | `max_cv_pct`; the optimize skill drops proxies that do not move with the journey |
| Risky changes went employees, then 1%, then wider; about 200 flags, over half removed by the end | rollout stages and flag tracking in the change log |
| More than 3,000 changes, no customer-facing incident or rollback; humans approved each change | rolled-back count; the optimize skill never merges or deploys |
| Named fixes: static composer in the HTML, V8 code cache, one message-ID lookup per tree (-48% instructions, -78% wall-clock), UTF-16 strings from an em dash | the demo's change log echoes them with invented numbers |

**Done means:**
- `setup` writes a project file with journeys from data and a CI guard; `measure` runs daily
  with keys or through the Datadog connector.
- The dashboard shows overall speedup, journeys against targets, regressions, a change
  ledger with field effects and proxies, and guardrail ceilings, at desktop and phone width
  in both themes.
- A write-up's measured numbers come only from `metrics.json`; hand-typed numbers are flagged.
- The four quality gates pass; the plugin and marketplace manifests validate.

## 3. Interview record
No interview was held; the request asked for the most complete plugin possible.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | Data sources | Monitoring and observability tools like Datadog | From request; Datadog API and connector first, Prometheus and files as well |
| 2 | Dashboard | Track application data and quantify optimizations | From request; section 4.6 |
| 3 | Write-up | Optional, blog style, all steps taken | From request; section 4.7 |
| 4 | Dashboard medium | claude.ai Artifact, as chronicle does | Coordinator default; assumed |
| 5 | Continuous | Optimize continuously | Daily `measure`, CI ratchet, regression suspects |
| 6 | Plugin name | speedup (first built as perf-ratchet) | Renamed at the owner's request, 21 Oct 2026 |

## 4. Proposal

### 4.1 Plugin contents (`plugins/speedup/`)
`skills/setup`, `skills/measure`, `skills/optimize`, `skills/report`, `agents/perf-gatherer.md`,
`agents/perf-writer.md` (Sonnet, Read and Write), `scripts/speedup`, the engine under
`src/speedup/` in the cli layout, `examples/demo/` and `examples/github-actions/`, MIT
license.

### 4.2 Sources (all read-only)
| Kind | Call | Notes |
| --- | --- | --- |
| `datadog-metric` | `GET /api/v1/query` | one series expected; more than one warns and uses the first |
| `datadog-rum` | `POST /api/v2/rum/analytics/aggregate` | a query body, the only POST allowed; see 7 and 10.1 |
| `prometheus` | `GET /api/v1/query_range`, one-day step | https, or http on localhost without a token |
| `file` | `import` of JSON or CSV | the Datadog connector path, other tools, exports |

Keys come from `DD_API_KEY` and `DD_APP_KEY` (or `.env`) and go only to a Datadog API host
from an allowlist pattern. The transport refuses any POST outside its allowlist before a
request is sent, retries 429 and 5xx with backoff, and never logs keys or query strings.

### 4.3 Computations in `core/` (no model involved)
- Day value: median of the day's points. Window value: median of its days. Default window 7
  days; baseline from the project file or the first window.
- Speedup: baseline over current (lower is better) or current over baseline; headline is the
  geometric mean across journeys.
- Regression: worse than the previous window by more than 5% with p < 0.05.
- Change effect: 7 days before against 7 days after the ship day, ship day skipped, 3 days
  minimum each side; verdict improved, regressed, no clear effect, too early or not shipped;
  overlapping changes listed.
- Priority: gap to target times weight, regressions first.
- Ratchet: fail above ceiling plus 1% tolerance; tighten to median plus 0.5% headroom;
  runs with a coefficient of variation over 2% never move a ceiling.

### 4.4 Commands
`init`, `measure`, `import`, `bench`, `guard`, `tighten`, `log`, `report`, `writeup`. Each
prints at most 15 lines. `guard` exits 2 over a ceiling; `report` exits 2 over the token cap;
`writeup` exits 2 on unknown keys or hand-typed numbers.

### 4.5 Files
In the repository: `perf/speedup.json` and `perf/changes.jsonl`, both meant to be committed.
In the data folder `~/speedup-runs/<project>/` (never committed): `history.json`,
`bench.json`, `raw/`, `metrics.json`, `digest.md` (12 KB cap), `budget.json`,
`dashboard.html`, `artifact.html`, `writeup.src.md`, `writeup.md`.

### 4.6 Dashboard
Inline CSS and SVG, no script, every source string escaped, links http(s) only. Sections:
summary band, speedup bars (log scale), one chart per journey with target, windows and ship
marks, priority table, change ledger, guardrail cards, write-up (sources folded), method.
Light and dark tokens; no horizontal scroll at 390 px. The styling follows the inspiration
post at the owner's request (21 Oct 2026): ivory paper, Source Serif 4 headlines, DM Sans
body, hairline rules, oat figure panels, a clay accent. The blog's own typefaces are not
free to embed, so these Google Fonts stand in.

### 4.7 Write-up
`perf-writer` reads `digest.md` and the outline and writes `writeup.src.md`, putting every
measured number as a `{{metrics.key}}` token. `writeup` fills them with units and formats,
appends a sources table and lists any digit typed into prose other than dates, years, ids,
percentile names, links and code. The outline mirrors the post: result first, what we
measured, finding the work, what we changed, keeping it fast, shipping safely, where it
stands, advice; 900 to 1,400 words.

### 4.8 Token budget
As RFC-0001: digest at most 3,000 tokens, outline plus writer instructions, 5,000 overhead,
6,000 output, 3,000 conversation, against a 25,000 default cap.

## 5. Alternatives considered
- **Extend impact-review or chronicle.** Rejected by principle 5: a different job, data
  source and audience.
- **Wall-clock benchmarks as the CI gate.** Rejected, as in the post: too noisy to fail a
  pull request on.
- **The Datadog API client library.** Rejected: a runtime dependency; two endpoints need
  only `urllib`.
- **Interactive dashboard with a chart library.** Rejected for 0.1: the static page renders
  in the Artifact, opens offline and cannot run injected script.
- **Mean or t-test for change effects.** Rejected: daily percentiles are skewed and the
  windows are short; a rank test fits.
- **Writer types numbers, a checker compares them.** Rejected: tokens make a wrong number
  impossible; the checker remains for stray digits.

## 6. Risks and objections
- **Confounded effects.** Several changes on one journey in one week share an effect.
  Mitigation: overlaps are listed on the dashboard, the digest and the write-up outline.
- **Minimum p-value at 7 days.** With 7 values a side the rank test bottoms out near 0.002;
  very small effects read as "no clear effect". Mitigation: `impact_days` up to 60.
- **Benchmarks run user commands.** Mitigation: argument lists only, no shell, a timeout;
  the commands come from the user's own committed project file.
- **Keys in the environment.** Mitigation: host allowlist, no logging, `.env` git-ignored,
  never written to the project file or the data folder.
- **Model-written prose about production.** Mitigation: `[ADD: ...]` placeholders for
  causes and lessons the data cannot show.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. New plugin speedup 0.1.0; marketplace
entry, ARCHITECTURE, CODEMAP, PROJECT, AGENTS, `.env.example`, `.gitignore`, pyproject test
paths.

**Constitution check:**
- Principle 1 (scripts compute, Claude writes): holds. Claude reads `digest.md` only.
- Principle 2 (every number has a source): holds, enforced by write-up tokens.
- Principle 3 (local and private): **tension** as in RFC-0004: the dashboard loads Google
  Fonts when opened. No collected data leaves the machine until the user publishes.
- Principle 4 (read-only against sources): holds for Datadog and Prometheus. `tighten` and
  `log` write the user's own project files; `optimize` edits the user's code with their
  approval. Neither is a source system.
- Guardrail "never call a write endpoint (POST ...)": **tension.** Datadog RUM aggregation
  is a POST that only reads. The transport allows that one path and refuses every other
  POST. Open question 10.1 proposes an amendment.
- Guardrail "no runtime dependency without an RFC": none added.

## 8. Cross-repo contract
N/A, internal.

## 9. Further optimizations, not built here
| # | Opportunity | Evidence | Effort |
| --- | --- | --- | --- |
| 1 | Datadog APM spans aggregation as a source | metrics cover APM p75 today, spans would add per-resource cuts | small |
| 2 | Segments: device class, country, network per journey | the post reported desktop and web separately | medium |
| 3 | Lighthouse CI and WebPageTest importers | teams without RUM | small |
| 4 | Change-point detection (CUSUM) to date regressions without a change log | suspects need logged changes today | medium |
| 5 | Bootstrap confidence intervals next to p-values | readers ask "how much", not only "whether" | small |
| 6 | A `prove` command: A/B by flag cohort from RUM attributes | flags already tracked | medium |
| 7 | Interactive journey charts (hover values) in the Artifact | static page shows values on cards only | small |
| 8 | Publish the write-up as its own Artifact page | blog drafts are shared apart from the dashboard | small |

## 10. Open questions
1. Amend the guardrail to "never call an endpoint that changes state; read-only query
   POSTs (GraphQL queries, Datadog analytics aggregate) are allowed by an allowlist"?
2. Accept Google Fonts in the dashboard under principle 3, as for chronicle, or ship system
   fonts only?
3. Defaults: 7-day windows, 5% regression threshold, 1% tolerance, 0.5% headroom, 2% noise
   limit. Keep?
4. Should `measure` support other monitoring MCP servers by name in `perf-gatherer`
   (New Relic, Grafana, Honeycomb), or keep the generic instructions?
5. Which of section 9 come next?
