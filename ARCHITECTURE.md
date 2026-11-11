# 10x-agent-marketplace — Architecture

> High-level technical truth. Names used here are the names used everywhere else — do not
> invent parallel vocabulary. Update in the same change as the thing it describes.

## Overview
This repo is a Claude Code plugin marketplace with no server.
Claude Code reads `.claude-plugin/marketplace.json`, and users install plugins from `plugins/<name>/`.
Each plugin runs on the user's own machine inside Claude Code.

The first plugin, impact-review, splits work in two so model tokens stay low:
a Python **collector** does every API call and every calculation, and Claude reads only the small **digest** it writes.

```
 user ──/impact-review:report──▶ Claude Code (skill)
                                   │ 1. runs collector (Bash)
                                   ▼
                         collector (Python, stdlib only)
                           │ GraphQL + REST, read-only token
                           ▼
                     GitHub API (github.com / GHE Cloud / GHES / ghe.com)
                           │
                           ▼
       run folder ~/impact-review-runs/<host>/<scope>/<since>_<until>/ (local, never committed)
         raw/  cached API responses   ← Claude never reads
         metrics.json, dashboard.md, dashboard.html, budget.json
         digest.md (12 KB cap), rubric.md  ← the impact-writer subagent reads only these
                           │ 2. skill checks budget.json, then invokes impact-writer (Sonnet)
                           ▼
         review.md, highlights.md, stories.md
```

The second plugin, chronicle (RFC-0002 and RFC-0003, drafts), builds illustrated story pages the same way:
code computes and paints, Claude writes and draws.

```
 user ──/chronicle:story──▶ Claude Code (skill)
                              │ 1. researcher subagent digests the material (read-only);
                              │    sources:gatherer reads company systems when sources is installed
                              ▼
            run folder chronicle-runs/<slug>/ (local, never committed)
              research/    facts.json (a locator on every fact) and material.md (a 12 KB digest)
              facts.json   company numbers by system, with queries.json and digest.md
              story.json   theme, chapters and blocks written by Claude; numbers as {{tokens}}
              art/*.svg    drawings by Claude; diagrams/*.svg, widgets/*.js optional
                              │ 2. scripts/chronicle build
                              ▼
              derive (code computes) → check → paint (OpenCV) → render (stdlib)
              build/artifact.html, build/art/*.webp, build/publish-files.json
                              │ 3. Artifact tool, after the user confirms
                              ▼
                     private claude.ai Artifact
```

chronicle's animation skill (RFC-0005, draft) and blueprint's architecture skill make
standalone animations the same way: Claude writes a painted scene or a drawing (chronicle),
or a TAD, sequence or ERD as data (blueprint), and the steps; code lays it out, times it and
exports it.

```
 user ──/chronicle:animation──▶ Claude Code (skill)
            run folder chronicle-runs/<slug>/: animation.json, facts.json, drawing.svg
                              │ scripts/chronicle animate build
                              ▼
              check → layout and routes (TAD) or sanitize (diagram) or paint (scene)
              → one SVG with CSS keyframes on one clock (stdlib)
              → frames from a local headless Chromium (DevTools pipe) → PNG, GIF (NumPy)
                and MP4 (local ffmpeg) or WebM (OpenCV)
              build/animation.svg, embed.html, index.html, poster.png, steps.png, animation.gif
```

The third plugin, speedup (RFC-0006, draft), runs a continuous performance loop the
same way: code fetches, computes and renders; Claude chooses journeys, changes code and
writes the post.

```
 user ──/speedup:setup | measure | optimize | report──▶ Claude Code (skills)
                              │ 1. scripts/speedup measure (keys)  or  perf-gatherer subagent + import (connector)
                              ▼
     Datadog metrics (GET) · Datadog RUM aggregate (read-only POST) · Prometheus (GET) · files
                              ▼
  repo: perf/speedup.json (journeys, targets, benchmarks, ceilings), perf/changes.jsonl (change log)
  data folder ~/speedup-runs/<project>/ (local, never committed)
    history.json, bench.json, raw/      ← Claude never reads
    metrics.json, digest.md (12 KB), budget.json, dashboard.html, artifact.html
                              │ 2. bench / guard / tighten run the user's proxy commands (argument lists)
                              │ 3. perf-writer (Sonnet) reads digest.md, writes writeup.src.md with {{key}} tokens
                              │ 4. writeup fills the tokens → writeup.md, re-renders the dashboard
                              ▼
                     private claude.ai Artifact (after the user confirms)
```

The fourth plugin, tokenwise, audits Claude Code's own session transcripts. Code parses
and judges every session; Claude reads only the digest and writes recommendations.

```
 Claude Code hooks ──Stop | PostToolUse(Bash) | PostToolUseFailure(Bash) | PreCompact──▶ scripts/tokenwise hook
 user ──/tokenwise:audit | handoff──▶ Claude Code (skills) ──▶ scripts/tokenwise audit | apply | undo | handoff
                              ▼
  ~/.claude/projects/<project>/<session>.jsonl and <session>/subagents/  (read-only)
                              ▼
  data folder ~/tokenwise-runs/<project>/ (local, never committed)
    findings.json, metrics.json, applied.json, state/   ← Claude never reads
    digest.md (12 KB), handoffs/*.md
                              │ low-risk fixes only → <project>/.claude/settings.local.json (logged, undoable)
```

## Components and repositories
| Component | Responsibility | Tech | Owner |
| --- | --- | --- | --- |
| Marketplace manifest `.claude-plugin/marketplace.json` | Lists every plugin and where it lives | JSON | Jacqueline Dean |
| impact-review plugin shell `plugins/impact-review/` (`.claude-plugin/plugin.json`, `skills/report/`, `agents/impact-writer.md`) | User-facing command; the skill runs the collector and hands the run folder to the `impact-writer` subagent (Sonnet, Read and Write only), which writes the synthesis | Markdown | Jacqueline Dean |
| impact-review collector `plugins/impact-review/src/impact_review/` | Calls GitHub through the linked sources package's transport, caches responses, computes metrics, renders dashboard and digest | Python 3.11+, standard library only at runtime | Jacqueline Dean |

| chronicle plugin shell `plugins/chronicle/` (`.claude-plugin/plugin.json`, `skills/story/`, `skills/animation/`, `agents/researcher.md`, `scripts/chronicle`) | The story workflow (brief, gather, write, build, publish) and the animation workflow (write, build, look, deliver) | Markdown, POSIX sh | Jacqueline Dean |
| chronicle builder `plugins/chronicle/src/chronicle/` | Facts and derive, story and widget checks, themes, diagram sanitizer, HTML renderer, page runtime (CSS and JS), SVG reader and watercolor painter; the animation timeline, GIF encoder and frame capture (TADs moved to blueprint) | Python 3.11+; standard library for rendering; NumPy and OpenCV for painting and raster exports; a local Chromium for frames and ffmpeg for MP4 | Jacqueline Dean |

| blueprint plugin `plugins/blueprint/` (`.claude-plugin/plugin.json`, `skills/{architecture,prototype}/`, `scripts/blueprint`, `src/blueprint/`, `examples/`) | Architecture, sequence and ERD figures and pages, and prototypes: write, check, build, look, publish | Python 3.11+, standard library; Markdown, POSIX sh; a local Chromium for frames | Jacqueline Dean |
| briefing plugin `plugins/briefing/` (`.claude-plugin/plugin.json`, `skills/{deck,dashboard}/`, `references/`, `scripts/briefing`, `src/briefing/`, `examples/`) | Decks and dashboards from facts: write, check, build, look, export, publish | Python 3.11+, standard library; Markdown, POSIX sh; a local Chromium for slide images and PDFs | Jacqueline Dean |
| sources plugin shell `plugins/sources/` (`.claude-plugin/plugin.json`, `agents/gatherer.md`, `skills/connect/`, `recipes/`, `scripts/sources`) | Reads company systems through the session's connectors or the script collectors into facts, queries and a digest; sets up each system | Markdown, POSIX sh | Jacqueline Dean |
| sources package `packages/sources/src/sources/` | Detection, the source picker, named connections, the facts and queries contract, the digest, the user-level database agent, the SQL guard, the HTTPS transport and the nine script-lane collectors (the GitHub one shared with impact-review) | Python 3.11+, standard library only; the user's `psql` and SQLcl | Jacqueline Dean |
| speedup plugin shell `plugins/speedup/` (`.claude-plugin/plugin.json`, `skills/{setup,measure,optimize,report}/`, `agents/perf-gatherer.md`, `agents/perf-writer.md`, `scripts/speedup`, `examples/`) | The optimization loop: choose journeys, measure, optimize against proxies, report and write up | Markdown, POSIX sh, YAML (CI example) | Jacqueline Dean |
| tokenwise plugin shell `plugins/tokenwise/` (`.claude-plugin/plugin.json`, `hooks/hooks.json`, `skills/{audit,handoff}/`, `scripts/tokenwise`) | Hooks after each turn and on Bash results and compaction; the audit and handoff skills | Markdown, JSON, POSIX sh | Jacqueline Dean |
| contributing plugin `plugins/contributing/` (`.claude-plugin/plugin.json`, `skills/{pull-request,branch-and-commit}/`) | PR descriptions, branch names and commit messages that follow each repo's own rules; no code | Markdown | Jacqueline Dean |
| tokenwise engine `plugins/tokenwise/src/tokenwise/` | Transcript parsing, weighted token usage, 14 audit rules, settings fixes and undo, loop guard, handoff facts, digest | Python 3.11+, standard library only | Jacqueline Dean |
| speedup engine `plugins/speedup/src/speedup/` | Project file checks, Datadog and Prometheus reads, imports, benchmark runner, statistics, ratchet, metrics, digest, dashboard, write-up tokens | Python 3.11+, standard library only | Jacqueline Dean |

The collector follows the standard `cli` layout (see CODEMAP.md):
`core/` holds metric rules with no I/O, `connectors/github/` holds every GitHub call,
`entrypoints/cli/` parses arguments, `config/` reads environment variables, and `__main__.py` wires them.

## Data flow
1. The user runs `/impact-review:report` with an optional scope (default the token's owner; also user lists, teams, organizations, an enterprise), timeframe (default year to date; any period up to all time), host and org filter.
2. The skill runs the collector through Bash.
3. The collector resolves the token and the scope's people (team, organization or enterprise members), then fetches each person's contributions, pull requests, reviews, issues and commits for the timeframe through `user(login:)` and merges them.
4. Raw responses are cached in the run folder, so a rerun makes no repeat API calls.
5. `core/` computes metrics; the CLI writes `metrics.json`, `dashboard.md`, `dashboard.html`, `digest.md`, `budget.json` and `rubric.md`. Over the token cap it exits 2 and the skill asks the user first.
6. The skill passes the run folder path to the `impact-writer` subagent, which reads `digest.md` and `rubric.md` only and writes the three synthesis files there.
7. The same collector runs without Claude: `PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --timeframe ytd`.

chronicle's code lives in two places (RFC-0007, spec 002). The shared engine,
`packages/chronicle-engine/src/chronicle_engine/`, uses the same layout: `core/story/` and
`core/motion/` hold the story rules, renderer, animation timeline, stage and the diagram
kind (no I/O), `connectors/` does every file read and write and drives a local browser,
ffmpeg and OpenCV's video writer, `entrypoints/cli/` parses arguments, `assets/` holds the
page's and the animations' stylesheet and script parts and the font list, and `registry.py`
holds the extension points. It imports no plugin. A page ships only the parts its figures
use, and the engine alone offers neutral chrome: a step progress bar, label and plain
chapter marks, ruled and card stats. chronicle links the engine into
`plugins/chronicle/src/chronicle_engine` (Claude Code copies linked files at install) and
registers its own parts from `plugins/chronicle/src/chronicle/pack.py`: the watercolor
painter as art provider, plates with pen notes, the creative chrome (arches, tracks,
routes, hang tags, receipts), the scene and rig kinds, the sameness review, `motifs`,
`research` and the widget library (`widgets`). Drawings may split a figure into a rig of
parts that turn about pivots by a gait; the page and the animations play the same rules.
The places blocks reuse plates and rigs: `panorama` (a wide painting to drag along, with
animals, zones, a tide and a journal), `rooms` (paintings joined by doorways) and `tour`
(a map whose stops open those scenes, walked by a route in the page's bar). With a
top-level `game`, quizzes play as holes against par, with a tally in the bar and a
`scorecard`. Records the reader makes (a round, a journal, the stops visited) stay in the
browser's storage on the reader's device; every write merges with what is stored.

briefing (RFC-0007, spec 002) turns facts into decks and dashboards on the same engine.
Its pack, `plugins/briefing/src/briefing/`, registers two layouts beside the engine's page:
a deck of 16:9 slides on a horizontal track and a dashboard of sections in a grid. It adds
KPI tiles whose status code sets by rule, filters over precomputed slices, and an
animation block that plays a built animation one step per click. It links the engine and
`packages/sources`, declares `"dependencies": ["sources"]`, and exports Slides and
Dashboard content, a PDF and a PNG per slide, and an upload manifest for Google Drive or
Microsoft 365 that Claude acts on only after the user confirms (constitution amendment 1).
`refresh` runs the script-lane queries again in-process over windows moved forward, then
rebuilds; facts read through connectors show as not refreshed. A brand kit, chosen with
`--brand`, lives in the engine, so every plugin's pages can share one look.

blueprint (RFC-0007, spec 002) draws systems and data designs on the same engine. Its pack,
`plugins/blueprint/src/blueprint/`, holds the TAD kind (moved from chronicle) and adds
sequence and ERD kinds, which write a drawing from data and play it through the engine's
diagram kind. Its architecture block wraps a built animation with part details, pins and a
step player; its prototype layout puts clickable screens behind tabs. `schema` reads a
Postgres or Oracle catalog live through the sources collectors, and `lineage` turns a
Databricks table's Unity Catalog lineage into a TAD. It links the engine and
`packages/sources` and declares `"dependencies": ["sources"]`.

sources (RFC-0007, spec 002) gives the data plugins read-only access to company systems.
Its code, `packages/sources/src/sources/`, uses the same layout and imports neither the
engine nor a plugin: `core/` detects which systems a session can reach, builds the source
picker, checks `facts.json` against `queries.json`, writes `digest.md` and holds the SQL
guard; `connectors/` holds the script-lane collector for each of the nine systems, one
HTTPS transport (GET, plus POST to named read-only paths) and the runners for the user's
`psql` and SQLcl, started with argument lists in read-only sessions; `config/` is the only
environment read. The plugin `plugins/sources/` links that package and adds the `gatherer`
subagent, one recipe per system and the user-run `/sources:connect`. It bundles no MCP
server: the gatherer reads the connectors the session already has or runs `sources
gather`, and databases with neither can go through a user-level `sources-db` agent whose
servers start only inside it. impact-review links the package too: its GitHub transport,
host endpoints and token lookup moved there, and its queries and parsing stayed.

speedup uses the same layout under `plugins/speedup/src/speedup/`: `core/`
(rules, statistics, rendering; no I/O), `connectors/datadog/`, `connectors/prometheus/`
and the shared `connectors/http.py` (every network call), `connectors/bench/` (runs
benchmark commands), `connectors/files/` (every file read and write), `entrypoints/cli/`,
`config/` (only env reads), `prompts/` (the write-up outline).

tokenwise uses the same layout under `plugins/tokenwise/src/tokenwise/`: `core/`
(transcript parsing, usage, rules, fixes, guard, handoff, digest; no I/O),
`connectors/files/` (every file read and write), `entrypoints/cli/` (commands and hooks),
`config/` (only env reads).

## Tech stack and tools
- Python 3.11+; runtime uses the standard library only (`urllib`, `json`), so installs need no package downloads.
- `uv` manages the dev environment: `ruff` (format and lint), `mypy` strict, `pytest`.
- GitHub GraphQL API v4 (contribution collection, search) and REST API v3 (repository contributor statistics).
- Claude Code plugin system: marketplace, plugins, skills, agents.
- chronicle: NumPy and OpenCV (painting and raster exports, fetched by `uv run --with`), vanilla JavaScript and SVG in the page, CSS keyframes in animations, Google Fonts chosen per page by the theme from `assets/fonts.json`; an installed Chromium or Chrome for screenshots and frames, and an installed ffmpeg for MP4.

## Deployment and environments
- No hosted environment; plugins run on each user's machine.
- Distribution: `/plugin marketplace add jacquelineadean/10x-agent-marketplace`, then `/plugin install impact-review@10x-agent-marketplace`, `chronicle@10x-agent-marketplace`, `briefing@10x-agent-marketplace` or `blueprint@10x-agent-marketplace` (each installs `sources` too), `sources@10x-agent-marketplace`, `speedup@10x-agent-marketplace`, `tokenwise@10x-agent-marketplace` or `contributing@10x-agent-marketplace`.
- Releases (RFC-0008, draft): each plugin carries a semantic version in `plugin.json` and its `marketplace.json` entry. release-please reads Conventional Commit PR titles on `main`, opens one release PR, and on merge tags `<plugin>-vX.Y.Z` (for example `impact-review-v1.0.0`) with a GitHub Release and a `plugins/<name>/CHANGELOG.md` entry. RELEASING.md has the steps and the deployment checklist.
- CI (GitHub Actions, `.github/workflows/`): `ci.yml` runs the four quality gates, `claude plugin validate .` and the version check on each PR and on `main`; `pr-lint.yml` checks PR titles and branch names; `release.yml` calls the reusable `release-please.yml`, which other repos call through `.github/release-kit/`.
- Rollback: revert the faulty PR, which cuts a patch release; or pin the marketplace entry to the previous tag.

## Boundaries and contracts
- Plugin to GitHub: the public GitHub APIs, versioned by GitHub; every call lives in `connectors/github/`.
- Skill to collector: command-line flags in, files out. The `metrics.json` and `digest.md` shapes carry a `schema_version` and are described in the plugin README.
- Single repo, so there is no `CONTRACTS/` folder.

## Cross-cutting concerns
- **Auth:** token from `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token --hostname <host>`. Read-only use only. Enterprise orgs with single sign-on need an SSO-authorized token. speedup reads `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`, `PROMETHEUS_URL`, `PROMETHEUS_TOKEN`; Datadog keys go only to Datadog API hosts, and a POST goes only to the RUM aggregation query path.
- **Privacy:** run folders hold corporate data. They live outside the repo by default, and `.gitignore` blocks them inside it. Nothing is sent anywhere except GitHub API requests.
- **Model tokens:** Claude never reads raw responses or `metrics.json` in full; the digest is capped at 12,000 bytes and `budget.json` checks the run against `--max-tokens` (default 25,000). In chronicle, briefing and blueprint, raw tool output and material stay inside the `sources:gatherer` and `researcher` subagents, which run on Sonnet as the impact-review and speedup writers do.
- **Untrusted text:** chronicle escapes every string from sources in HTML and in the page's JSON blob; links allow only http(s) and page anchors.
- **Rate limits:** GraphQL allows 5,000 points per hour; the collector caches, paginates in pages of 100 and backs off on secondary limits.
- **Secrets in logs:** the collector never prints the token or request headers.
- **Observability:** progress and warnings go to stderr; outputs go to files.

## Local development
```bash
uv sync                                   # install dev tools
uv run pytest                             # tests
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/impact-review/src/impact_review   # strict type check
uv run mypy packages/chronicle-engine/src/chronicle_engine
uv run mypy plugins/chronicle/src/chronicle
uv run mypy plugins/speedup/src/speedup
uv run mypy plugins/tokenwise/src/tokenwise
uv run mypy packages/sources/src/sources
uv run mypy plugins/briefing/src/briefing
uv run mypy plugins/blueprint/src/blueprint
claude plugin validate .                  # marketplace and plugin manifests
claude --plugin-dir plugins/impact-review # try the plugin in Claude Code
plugins/chronicle/scripts/chronicle build plugins/chronicle/examples/keystone/story.json --out /tmp/keystone
```
