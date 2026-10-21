---
name: measure
description: Pull the latest p75 values for every journey from Datadog, Prometheus or files, rebuild the performance dashboard, and flag regressions with likely suspects. Use for a daily or on-demand performance check, "did anything get slower", "how fast are we now", or as the scheduled step of continuous optimization.
argument-hint: "[--days N] [--journey ID]"
---

# /perf-ratchet:measure

Runs the measuring half of the loop: fetch, compute, compare. Code does all math. You read
only the command's printed lines and, when needed, `digest.md`.

## 1. Fetch
Use the first that applies:
- `DD_API_KEY` and `DD_APP_KEY` (or Prometheus settings) are set:
  ```bash
  "${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" measure --days 14
  ```
- A Datadog connector is available in Claude: invoke the `perf-gatherer` subagent with
  `Mode: measure. Project file: perf/ratchet.json. Window: <today-14>..<yesterday>. Write
  <data folder>/imports/`, then:
  ```bash
  "${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" import <data folder>/imports/*.json
  ```
- Neither: say which keys or connector are missing in one line and stop.

`file` journeys are skipped by `measure`; they update only through `import`.

## 2. Compute
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/perf-ratchet" report
```
It prints at most 15 lines: overall speedup, journeys at target, regressions, the top three
gaps, the token estimate. Exit 2 here only means the digest estimate is over the cap; the
dashboard is still written.

## 3. Regressions
For each `REGRESSION <journey>` line, read the `## Journeys` and `## Changes` sections of
`<data folder>/digest.md` and name suspects: changes on that journey shipped inside the
current or previous window, with their flag. A suspect behind an open flag can be turned
off; say so. Do not claim a cause; the rank test shows a shift, not who caused it.

## 4. Reply
At most 8 lines: overall speedup, journeys at target, each regression with its suspects,
the top gap, and the dashboard path (`<data folder>/dashboard.html`). Offer
`/perf-ratchet:report` to publish the dashboard and `/perf-ratchet:optimize <journey>`
for the top gap.

## Never
- Never read `raw/`, `history.json` or `metrics.json` into the conversation.
- Never change monitors, dashboards or flags in a source system.
