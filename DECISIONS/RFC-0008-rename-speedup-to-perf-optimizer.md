---
id: RFC-0008
title: "Rename speedup to perf-optimizer"
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude Code session, 31 Oct 2026 (RFC-0007 interview, answers 9 and 16)
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0006, RFC-0007]
author: Claude Code, for Jacqueline Dean
created: 2026-10-31
---

# RFC-0008 Rename speedup to perf-optimizer

## 1. Summary
The speedup plugin (RFC-0006) becomes perf-optimizer 0.2.0.
The owner asked for a technical name during the RFC-0007 interview and chose `perf-optimizer` from three candidates.
The rename changes the product name and keeps the measure named speedup: the ratio of a baseline time to a current time.
Four names live in adopters' repositories and machines: the project file, two environment variables and the data folder.
Each one keeps a fallback until perf-optimizer 1.0.0, and a shim keeps copied CI workflows running for the same period.

Status: draft. Nothing is built.

## 2. The need
- "speedup" names the plugin and also a measure it reports: `geomean_speedup`, "Overall speedup" and the speedup bars chart. A reader cannot tell the product from the number.
- The request asks for a technical name that says what the plugin does.
- The word appears 328 times in 59 files outside `uv.lock`, RFC-0006 and RFC-0007. The plugin's own code uses the measure sense 29 times.
- The CI example clones the marketplace's default branch and runs `plugins/speedup/src`. A bare folder rename breaks every repository that copied it, on its next CI run.

## 3. Interview record
| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | Should speedup move onto RFC-0007's shared sources and charts? | No, it stays separate (RFC-0007 answer 9) | Only the name changes |
| 2 | New name | `perf-optimizer` (RFC-0007 answer 16) | Package `perf_optimizer`, commands `/perf-optimizer:setup` and the rest |
| 3 | How long do fallbacks last? | Proposed: until 1.0.0 | Open (10.1) |

## 4. Proposal

### 4.1 What changes name
| Today | After |
| --- | --- |
| plugin `speedup`, folder `plugins/speedup/`, marketplace entry `speedup` | `perf-optimizer`, `plugins/perf-optimizer/`, entry `perf-optimizer` |
| Python package `speedup`, `python -m speedup` | `perf_optimizer`, `python -m perf_optimizer` |
| launcher `scripts/speedup` | `scripts/perf-optimizer` |
| skills `/speedup:setup`, `/speedup:measure`, `/speedup:optimize`, `/speedup:report` | `/perf-optimizer:setup`, `:measure`, `:optimize`, `:report` |
| project file `perf/speedup.json` | `perf/perf-optimizer.json` |
| `SPEEDUP_CONFIG`, `SPEEDUP_RUNS` | `PERF_OPTIMIZER_CONFIG`, `PERF_OPTIMIZER_RUNS` |
| data folder `~/speedup-runs/` | `~/perf-optimizer-runs/` |
| User-Agent `speedup/0.1.0` | `perf-optimizer/0.2.0` |
| dashboard brand "speedup" | "perf-optimizer" |
| CI example `examples/github-actions/speedup.yml` | `perf-optimizer.yml` |
| tests `test_speedup_*.py`, `speedup_helpers.py` | `test_perf_optimizer_*.py`, `perf_optimizer_helpers.py` |

The agents `perf-gatherer` and `perf-writer` keep their names. `perf/changes.jsonl` keeps its name.

### 4.2 What keeps the name
The measure keeps it: `geomean_speedup`, `numbers.speedup()`, `speedup_bars`, "Overall speedup" and every "×1.8 speedup" label.
A search-and-replace would rename the measure too, so the edits are made by hand and reviewed.
A test fails when `speedup` appears in a path, a command, an environment variable name or the brand outside the fallback code.
RFC-0006 stays as written, because it records a past decision.

### 4.3 Fallbacks until 1.0.0
| Old name | Read when | Message on stderr, once per run |
| --- | --- | --- |
| `perf/speedup.json` | `perf/perf-optimizer.json` is missing | "Using perf/speedup.json. Rename it: git mv perf/speedup.json perf/perf-optimizer.json" |
| `SPEEDUP_CONFIG`, `SPEEDUP_RUNS` | the new names are unset | "SPEEDUP_CONFIG is deprecated. Set PERF_OPTIMIZER_CONFIG." |
| `~/speedup-runs/<project>/` | the new folder is missing and the old one exists | "Using ~/speedup-runs/<project>. Move it to ~/perf-optimizer-runs/." |

`init` writes only the new names. No fallback moves or rewrites an adopter's files.
`.gitignore` gains `perf-optimizer-runs/` and keeps `speedup-runs/`.

### 4.4 Copied CI workflows
- A shim stays at `plugins/speedup/src/speedup/` until 1.0.0. Its `__main__.py` puts `plugins/perf-optimizer/src` on the import path, prints one deprecation line and runs `perf_optimizer`. The shim folder has no manifest, so the marketplace lists no `speedup` plugin.
- The new example clones a release tag, `perf-optimizer-v0.2.0` under ARCHITECTURE.md's tag scheme, so a later release cannot break an adopter's CI.
- The plugin README opens with the two lines adopters change in their workflow.

### 4.5 Installed plugins
Claude Code keeps an installed `speedup` working from its cache, but `/plugin update speedup` then finds no marketplace entry.
The README and the release notes give the two commands:

```
/plugin uninstall speedup@10x-agent-marketplace
/plugin install perf-optimizer@10x-agent-marketplace
```

### 4.6 Files that change
- `plugins/speedup/` moves to `plugins/perf-optimizer/`; the shim of 4.4 stays behind.
- `.claude-plugin/marketplace.json`, `pyproject.toml` test and source paths, `.gitignore`, `.env.example`.
- `ARCHITECTURE.md`, `PROJECT.md` (the glossary's data folder entry), `CODEMAP.md`, `AGENTS.md` (the mypy command, the run folder list, the test file names) and `DECISIONS/README.md`.

## 5. Alternatives considered
- **performance-optimizer.** The owner's first suggestion; its commands run longer (`/performance-optimizer:measure`).
- **perf-ratchet.** The plugin's first name. It names the CI ceiling, one of the plugin's four jobs.
- **Keep `perf/speedup.json` for good.** No churn in adopters' repositories, but the file and the product would carry different names.
- **Rename with no fallbacks or shim.** Simplest; every adopter's CI and config breaks on the next run.

## 6. Risks and objections
- **Adopters miss the deprecation lines.** The fallbacks and the shim keep config and CI working until 1.0.0, and the README's first section says what to change.
- **A hand edit misses a product mention or renames the measure.** The test in 4.2 and a reviewed diff catch both.
- **Two folder names for one plugin until 1.0.0.** The shim holds one file and imports the real package, so no code is copied.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. speedup 0.1.0 becomes perf-optimizer 0.2.0.
**Constitution check:** no principle changes. No new dependency. The plugin stays local and read-only against Datadog and Prometheus.

## 8. Cross-repo contract
Adopters' repositories hold `perf/speedup.json`, `perf/changes.jsonl` and a copied workflow. 4.3 and 4.4 keep all three working until 1.0.0.

## 9. Out of scope
- Any change to measuring, benchmarks, the ratchet or the reports.
- Moving perf-optimizer onto `packages/sources` or the engine's charts; RFC-0007 keeps it separate.

## 10. Open questions
1. Keep the fallbacks and the CI shim until 1.0.0, or remove them in 0.3.0?
2. Rename the project file to `perf/perf-optimizer.json`, or keep `perf/speedup.json` as the one old name that stays?
