---
name: optimize
description: Run one optimization cycle on the slowest user journey: find the hot path, build a deterministic proxy benchmark, make the change, prove it with before and after numbers, guard it with a CI ceiling that only moves down, and log it for the dashboard. Use when someone asks to make the app faster, fix a slow page, endpoint or interaction, or work the next item from speedup.
argument-hint: "[journey id]"
---

# /speedup:optimize

One cycle of the method from "How we made claude.ai 3x faster in two weeks": measure in the
field, optimize against a number that only goes down, ship behind a flag, keep the win with
a guardrail. Repeat per journey. A person approves every change before it merges.

## 1. Pick the journey
If the user named one, use it. Otherwise run `report` and take the first `next:` line; a
regressed journey always comes first. Read only the `## Journeys`, `## Where to look next`
and `## Changes` sections of `<data folder>/digest.md`, for that journey's baseline,
current, target and earlier changes.

## 2. Find where the time goes
Trace the journey through the code from the user's action to the moment they can act.
Measure before reading deeply; pick the tool that fits:
- Browser: a Chrome performance trace or Playwright with `page.metrics()`, React Profiler
  commit counts, `PerformanceObserver` for long tasks and layout shifts, bundle analysis
  for the first load.
- Node and Electron: `node --cpu-prof`, `--trace-deopt`, V8 code cache status.
- Backend: the slowest APM spans for the endpoint, `EXPLAIN ANALYZE` on its queries.
- Pure functions: `valgrind --tool=cachegrind` instruction counts.

Write down the top three costs with numbers before changing anything.

## 3. Build a proxy benchmark
Wall-clock time is too noisy to gate code on. The proxy is a command that prints one stable
number for the hot path:
- instruction count of a pure JavaScript path under valgrind (`node --jitless`, so the
  count does not depend on JIT timing);
- React commits, DOM mutations or layout counts for a scripted interaction;
- bytes shipped on the first load; queries per request.

Add it to `perf/speedup.json` under `benchmarks` (`command` as an argument list, `parse`
of `number`, `valgrind`, `json` or `regex`, `journeys`), then check it:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/speedup" bench --benchmark <id> --repeat 5
```
Keep it only if the coefficient of variation is at most 2% and the number moves with the
journey (a change that slows the journey must raise it). Otherwise rework or drop it, and
say why. A benchmark that does not track user latency is worse than none.

## 4. Change the code
- Smallest change that removes the measured cost. One idea per change.
- Re-run `bench` after; record the before and after numbers.
- Run the project's own tests and linters.
- Risky changes go behind a feature flag with a staged rollout: employees, then 1%, then
  wider. Use the project's flag system; never invent one.

## 5. Lock in the win
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/speedup" tighten --benchmark <id>
```
The ceiling drops to the new number plus 0.5% headroom. From now on `guard` fails any pull
request that pushes the proxy over it. Ceilings never go up by themselves; raising one is a
hand edit with a reason in the pull request.

## 6. Log the change
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/speedup" log --title "<what changed, in user terms>" \
  --journey <id> --benchmark <id> --before <n> --after <n> --flag <name> --stage dev --pr <url>
```
Update it as it rolls out: `log --id c-00NN --stage 1%`, then `--stage 100% --shipped
YYYY-MM-DD`, and `--flag-removed` when the flag is deleted. The field effect appears on the
dashboard once 3 days of data exist on each side of the ship day.

## 7. Report
Reply with: the journey, the cost found (numbers), the change, the proxy before and after,
the new ceiling, and what is left for a person: review, flag rollout, merge. Open a pull
request only if the user asked for one or the repository's workflow says to.

## Never
- Never merge, deploy or flip a production flag yourself.
- Never raise a ceiling to make `guard` pass.
- Never write a field number (p75, speedup) from memory; they come from `report`.
