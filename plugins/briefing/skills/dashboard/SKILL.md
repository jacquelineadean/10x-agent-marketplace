---
name: dashboard
description: Build a KPI dashboard or executive overview from facts as an interactive HTML Artifact, with KPI tiles (value, target, change, sparkline, status), charts, tables, filters over precomputed slices, an as-of stamp and the query behind every number; or as claude.ai's Dashboard type. Use for executive overviews, KPI and metrics reviews, operational health, migration and program status, and team scorecards. For illustrated stories use chronicle; for system diagrams use blueprint.
---

# Dashboards from facts

A dashboard is a header with its as-of stamp, then sections of KPI tiles, charts and
tables in a grid. Code sets each tile's status by rule and formats every number; every
number shows its source and query on hover. You choose the measures and write the words.

| Step | Who | Output (run folder) |
| --- | --- | --- |
| 1. Brief | you, with the user; `briefing new --layout dashboard` | `story.json` |
| 2. Facts | `sources:gatherer`, or the user's pasted numbers | `facts.json`, `queries.json`, `digest.md` |
| 3. Write | you | `story.json` |
| 4. Build and look | `briefing build`, then `briefing shoot` | `build/artifact.html`, `build/shots/*.png` |
| 5. Publish | you, after the user confirms | an Artifact or claude.ai's Dashboard type |

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" new briefing-runs/<slug> --layout dashboard --title "Title"
```
Add `--brand repo`, `--brand config` or `--brand PATH` to copy a brand kit into the folder.
Read `${CLAUDE_PLUGIN_ROOT}/references/brand.md` when the user has a house style.

## 1. Brief
Ask only what the request leaves open, in one AskUserQuestion: who reads it and what they
decide with it, the measures and their targets, the window, the systems to read, and any
breakdown to filter by (team, region, product).

## 2. Facts
Call `sources:gatherer` with `Mode: gather`, the run folder, the systems, the window and
the brief. Ask it for each filter's slices as separate facts (`delivery.payments.deploys`,
`delivery.search.deploys`). When the request names no system, run
`"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" sources detect --picker --connectors <names>`, where
`<names>` lists the MCP server names in your tool list, and pass its output as
AskUserQuestion's `questions`. Read `digest.md`, never `facts.json` or tool output.

## 3. Write
Read `references/dashboard-format.md` and `${CLAUDE_PLUGIN_ROOT}/references/voice.md`.
- Open with a `kpi` block: each tile names a fact, a target and which way is better.
- Give each chart a title that says what changed, and a source.
- Put a `filters` block where the breakdown starts; mark each block that changes with it
  `"slice": "<filter key>"` and write `{<filter key>}` where its fact paths change.

## 4. Build and look
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" check briefing-runs/<slug>/story.json
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" build briefing-runs/<slug>/story.json
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" shoot briefing-runs/<slug>/story.json
```
Every KPI needs a target and a query; stale facts and unsourced numbers show as warnings.
Look at both screenshots with the Read tool before publishing.

## 5. Publish
Confirm the destination with the user first.
- **Artifact** (default): publish `build/artifact.html` with the Artifact tool.
- **Dashboard** (`--to dashboard`): run `briefing export <story> --to dashboard`, then start
  from claude.ai's Dashboard type (Artifact quickstart, intent `other`) and fill it from
  `build/dashboard.json`: tiles, statuses, as-of date and sources as written there.

## 6. Refresh
`briefing refresh <story>` reads the script-lane queries again, each window moved to end
with the last complete period, and rebuilds with no model call. The stamp shows the new
date; numbers from connectors show "Not refreshed" until the gatherer runs again. Republish
`build/artifact.html` to the same Artifact.
