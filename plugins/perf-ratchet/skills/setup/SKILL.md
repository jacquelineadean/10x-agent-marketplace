---
name: setup
description: Set up continuous performance work for an application: choose the user journeys to speed up from Datadog RUM, APM or Prometheus data, set p75 targets and a baseline, write perf/ratchet.json, add the CI guardrail, and take the first measurement. Use when someone wants to start optimizing app performance, track web or API speed, or set up perf-ratchet in a repo.
argument-hint: "[project name] [--source datadog|prometheus|files]"
---

# /perf-ratchet:setup

Goal: a committed `perf/ratchet.json` that names 5 to 15 journeys with targets, a baseline
window, a first measurement and a CI job that runs `guard`. Scripts compute; you choose
journeys with the user and write the file.

A journey is one thing a user does, timed from their side of the screen: "fresh load to a
typeable composer", "switch conversation", "search results shown", "API: create order".
Page-level averages hide where people wait; journeys name it.

## 1. Find the runner
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" --help
```
It needs `uv` or Python 3.11+. Without either, stop and say how to install uv.

## 2. Start the project file
In the user's repository root:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" init --project "<name>"
```
It writes `perf/ratchet.json` (two example journeys) and an empty `perf/changes.jsonl`.

## 3. Choose journeys from the data
Pick the path that works, in this order:
1. **Datadog connector in Claude.** Invoke the `perf-gatherer` subagent with:
   `Mode: discover. Window: last 28 days. Write <data folder>/candidates.md.` The data folder
   is `~/perf-ratchet-runs/<project>/`. It lists RUM views and actions, APM endpoints and
   custom timing metrics by traffic with their p75, as candidates only.
2. **Datadog API keys** (`DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`): ask the user for the RUM
   application, the views and actions that matter, and the APM services. Do not list
   resources with raw API calls yourself.
3. **Prometheus** (`PROMETHEUS_URL`): ask for the histogram metric names per route.
4. **No monitoring access:** journeys can be fed from files (`import`), for example CSV
   exports from another tool or Lighthouse runs. Say this is the fallback.

Agree the list with the user in one message: a table of journey, why it matters, current
p75 if known, proposed target and weight. Then write the journeys into the project file.

Rules for each journey:
- `source.kind`: `datadog-rum` (measure such as `@view.loading_time` or
  `@view.custom_timings.<name>`, `aggregation: pc75`, `scale: 1e-6` because RUM durations
  are nanoseconds), `datadog-metric` (a query that returns one series, such as
  `p75:trace.http.request{service:web,env:prod}`, `scale: 1000` for seconds), `prometheus`
  (a `histogram_quantile(0.75, ...)` query over a `[1d]` range, `scale: 1000`; the value
  read at midnight is filed under the day that just ended), or `file`.
- `target`: from a product goal when one exists; otherwise ask. Never invent one silently;
  a journey may go without a target and is then tracked but not prioritized.
- `weight`: traffic share times importance, 1 to 5. Revenue or first-impression journeys
  get the most.
- `direction`: `higher` only for throughput-style journeys.
- Prefer a custom timing that ends when the user can act (composer typeable, results
  painted) over generic load events.

Set `baseline` to the last 7 full days before any optimization starts, unless the user
names another period.

## 4. Take the first measurement
- With keys: `"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" measure --days 28`.
- With the connector: invoke `perf-gatherer` with `Mode: measure. Project file: <path>.
  Window: <since>..<until>. Write <data folder>/imports/`. Then
  `"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" import <data folder>/imports/*.json`.

Then `"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" report`. Show its lines.

## 5. Add the guardrail to CI
Copy `${CLAUDE_PLUGIN_ROOT}/examples/github-actions/perf-ratchet.yml` to
`.github/workflows/perf-ratchet.yml` and adjust the install step. It runs `guard` on every
pull request and `tighten` daily, opening a pull request when ceilings move down. It does
nothing until benchmarks exist; `/perf-ratchet:optimize` adds them.

## 6. Continuous measurement
Offer one of these, and set it up only on a yes:
- A daily cloud routine or `/loop 1d /perf-ratchet:measure` in Claude Code.
- A scheduled CI job running `measure` and `report` with the keys as secrets.

## 7. Report
Reply with the journey table (current p75, target, gap), the files written, and the next
command: `/perf-ratchet:optimize`.

## Never
- Never put API keys in the project file, a commit or the conversation. Keys live in the
  environment or `.env`, which stays git-ignored.
- Never create, edit or delete anything in Datadog or Prometheus.
- Never read `raw/` or `history.json` into the conversation.
