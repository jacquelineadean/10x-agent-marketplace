---
name: report
description: Publish the performance dashboard as a private claude.ai Artifact (overall speedup, journeys against targets, change ledger with measured effects, guardrail ceilings) and optionally write a blog-style post of every step taken, with each number filled in from the data. Use when someone wants a performance dashboard, to quantify optimizations, share results, or write up how the app got faster.
argument-hint: "[--writeup] [--max-tokens N]"
---

# /speedup:report

Code renders the dashboard and fills every number. You publish it and, with `--writeup`
or when the user asks for a write-up, hand the prose to the `perf-writer` subagent.

## 1. Render
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/speedup" report [--max-tokens N]
```
Show the printed lines (at most 15). Files land in the data folder:
`dashboard.html` (opens from disk), `artifact.html` (the Artifact body), `metrics.json`,
`digest.md`, `budget.json`.

Exit 2 means the token estimate is over the cap (default 25,000). The dashboard is fine to
publish. Before a write-up, ask the user to choose: raise `--max-tokens`, go ahead with the
digest as trimmed, or skip the write-up.

## 2. Write-up (optional)
Only with `--writeup` or an explicit ask. Invoke `perf-writer` with exactly:
`Data folder: <path>. Read digest.md there and ${CLAUDE_PLUGIN_ROOT}/src/speedup/prompts/writeup-outline.md, then write writeup.src.md into the data folder.`

Then fill the numbers and re-render:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/speedup" writeup
```
- Exit 0: `writeup.md` is written, with a sources table, and the dashboard gains a
  Write-up section.
- Exit 2: it lists unknown keys or numbers typed by hand. Send those lines to
  `perf-writer` once, asking it to fix only those spots, then run `writeup` again. If it
  still fails, publish anyway and tell the user which spots to check.

## 3. Publish
- Ask once before the first publish: the page is private to the user but hosted on
  claude.ai, and it holds production performance data.
- Publish `<data folder>/artifact.html` with the Artifact tool, `icon: "chart"`, and a
  description such as "p75 speed of N user journeys, changes shipped and their measured
  effect." The page has no scripts and loads only Google Fonts.
- To update, republish the same file path (or the artifact `url` in a later
  conversation); the link stays the same.

## 4. Reply
The link, the overall speedup line, journeys at target, and, with a write-up, its title and
`writeup.md` path. If the user wants the post outside claude.ai, `writeup.md` is plain
Markdown ready for a blog.

## Never
- Never read `metrics.json`, `history.json` or `raw/` into the conversation.
- Never type a measured number into a message that the report lines did not print.
