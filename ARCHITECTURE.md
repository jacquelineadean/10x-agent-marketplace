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
       run folder ~/impact-review-runs/<host>/<login>/<since>_<until>/ (local, never committed)
         raw/  cached API responses   ← Claude never reads
         metrics.json, dashboard.md, dashboard.html, budget.json
         digest.md (12 KB cap), rubric.md  ← the impact-writer subagent reads only these
                           │ 2. skill checks budget.json, then invokes impact-writer (Sonnet)
                           ▼
         self-evaluation.md, resume-bullets.md, interview-stories.md
```

The second plugin, chronicle (RFC-0002 and RFC-0003, drafts), builds illustrated story pages the same way:
code computes and paints, Claude writes and draws.

```
 user ──/chronicle:story──▶ Claude Code (skill)
                              │ 1. chronicle-gatherer subagent queries connected tools (read-only)
                              ▼
            run folder chronicle-runs/<slug>/ (local, never committed)
              facts.json   every number: value, unit, source, note; derive table
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

chronicle's animation skill (RFC-0005, draft) makes standalone animations the same way:
Claude writes a TAD as data, a drawing or a painted scene, and the steps; code lays it
out, times it and exports it.

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

The third plugin, perf-ratchet (RFC-0006, draft), runs a continuous performance loop the
same way: code fetches, computes and renders; Claude chooses journeys, changes code and
writes the post.

```
 user ──/perf-ratchet:setup | measure | optimize | report──▶ Claude Code (skills)
                              │ 1. scripts/perf-ratchet measure (keys)  or  perf-gatherer subagent + import (connector)
                              ▼
     Datadog metrics (GET) · Datadog RUM aggregate (read-only POST) · Prometheus (GET) · files
                              ▼
  repo: perf/ratchet.json (journeys, targets, benchmarks, ceilings), perf/changes.jsonl (change log)
  data folder ~/perf-ratchet-runs/<project>/ (local, never committed)
    history.json, bench.json, raw/      ← Claude never reads
    metrics.json, digest.md (12 KB), budget.json, dashboard.html, artifact.html
                              │ 2. bench / guard / tighten run the user's proxy commands (argument lists)
                              │ 3. perf-writer (Sonnet) reads digest.md, writes writeup.src.md with {{key}} tokens
                              │ 4. writeup fills the tokens → writeup.md, re-renders the dashboard
                              ▼
                     private claude.ai Artifact (after the user confirms)
```

## Components and repositories
| Component | Responsibility | Tech | Owner |
| --- | --- | --- | --- |
| Marketplace manifest `.claude-plugin/marketplace.json` | Lists every plugin and where it lives | JSON | Jacqueline Dean |
| impact-review plugin shell `plugins/impact-review/` (`.claude-plugin/plugin.json`, `skills/report/`, `agents/impact-writer.md`) | User-facing command; the skill runs the collector and hands the run folder to the `impact-writer` subagent (Sonnet, Read and Write only), which writes the synthesis | Markdown | Jacqueline Dean |
| impact-review collector `plugins/impact-review/src/impact_review/` | Calls GitHub, caches responses, computes metrics, renders dashboard and digest | Python 3.11+, standard library only at runtime | Jacqueline Dean |

| chronicle plugin shell `plugins/chronicle/` (`.claude-plugin/plugin.json`, `skills/story/`, `skills/animation/`, `agents/chronicle-gatherer.md`, `scripts/chronicle`) | The story workflow (brief, gather, write, build, publish) and the animation workflow (write, build, look, deliver) | Markdown, POSIX sh | Jacqueline Dean |
| chronicle builder `plugins/chronicle/src/chronicle/` | Facts and derive, story and widget checks, themes, diagram sanitizer, HTML renderer, page runtime (CSS and JS), SVG reader and watercolor painter; the animation timeline, TAD layout and routing, GIF encoder and frame capture | Python 3.11+; standard library for rendering; NumPy and OpenCV for painting and raster exports; a local Chromium for frames and ffmpeg for MP4 | Jacqueline Dean |

| perf-ratchet plugin shell `plugins/perf-ratchet/` (`.claude-plugin/plugin.json`, `skills/{setup,measure,optimize,report}/`, `agents/perf-gatherer.md`, `agents/perf-writer.md`, `scripts/perf-ratchet`, `examples/`) | The optimization loop: choose journeys, measure, optimize against proxies, report and write up | Markdown, POSIX sh, YAML (CI example) | Jacqueline Dean |
| perf-ratchet engine `plugins/perf-ratchet/src/perf_ratchet/` | Project file checks, Datadog and Prometheus reads, imports, benchmark runner, statistics, ratchet, metrics, digest, dashboard, write-up tokens | Python 3.11+, standard library only | Jacqueline Dean |

The collector follows the standard `cli` layout (see CODEMAP.md):
`core/` holds metric rules with no I/O, `connectors/github/` holds every GitHub call,
`entrypoints/cli/` parses arguments, `config/` reads environment variables, and `__main__.py` wires them.

## Data flow
1. The user runs `/impact-review:report` with an optional timeframe (default year to date), host and org filter.
2. The skill runs the collector through Bash.
3. The collector resolves the token, identifies the user, then fetches contributions, pull requests, reviews, issues and commits for the timeframe.
4. Raw responses are cached in the run folder, so a rerun makes no repeat API calls.
5. `core/` computes metrics; the CLI writes `metrics.json`, `dashboard.md`, `dashboard.html`, `digest.md`, `budget.json` and `rubric.md`. Over the token cap it exits 2 and the skill asks the user first.
6. The skill passes the run folder path to the `impact-writer` subagent, which reads `digest.md` and `rubric.md` only and writes the three synthesis files there.
7. The same collector runs without Claude: `PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --timeframe ytd`.

chronicle uses the same layout under `plugins/chronicle/src/chronicle/`: `core/story/` and
`core/watercolor/` hold the rules and the painting (no I/O), `core/motion/` holds the
animation timeline, stage, kinds and GIF encoder (no I/O), `connectors/files/` does every
file read and write, `connectors/browser/` drives a local browser, `connectors/video/`
runs ffmpeg and OpenCV's video writer, `entrypoints/cli/` parses arguments, and `assets/`
holds the page's and the animations' stylesheet parts and the font list.

perf-ratchet uses the same layout under `plugins/perf-ratchet/src/perf_ratchet/`: `core/`
(rules, statistics, rendering; no I/O), `connectors/datadog/`, `connectors/prometheus/`
and the shared `connectors/http.py` (every network call), `connectors/bench/` (runs
benchmark commands), `connectors/files/` (every file read and write), `entrypoints/cli/`,
`config/` (only env reads), `prompts/` (the write-up outline).

## Tech stack and tools
- Python 3.11+; runtime uses the standard library only (`urllib`, `json`), so installs need no package downloads.
- `uv` manages the dev environment: `ruff` (format and lint), `mypy` strict, `pytest`.
- GitHub GraphQL API v4 (contribution collection, search) and REST API v3 (repository contributor statistics).
- Claude Code plugin system: marketplace, plugins, skills, agents.
- chronicle: NumPy and OpenCV (painting and raster exports, fetched by `uv run --with`), vanilla JavaScript and SVG in the page, CSS keyframes in animations, Google Fonts chosen per page by the theme from `assets/fonts.json`; an installed Chromium or Chrome for screenshots and frames, and an installed ffmpeg for MP4.

## Deployment and environments
- No hosted environment; plugins run on each user's machine.
- Distribution: `/plugin marketplace add jacquelineadean/10x-agent-marketplace`, then `/plugin install impact-review@10x-agent-marketplace`, `chronicle@10x-agent-marketplace` or `perf-ratchet@10x-agent-marketplace`.
- Releases: each plugin carries a semantic version in `plugin.json`; a git tag `<plugin>-vX.Y.Z` (for example `impact-review-v1.0.0`) marks each release.
- Rollback: reinstall from the previous tag, or pin the marketplace to it.

## Boundaries and contracts
- Plugin to GitHub: the public GitHub APIs, versioned by GitHub; every call lives in `connectors/github/`.
- Skill to collector: command-line flags in, files out. The `metrics.json` and `digest.md` shapes carry a `schema_version` and are described in the plugin README.
- Single repo, so there is no `CONTRACTS/` folder.

## Cross-cutting concerns
- **Auth:** token from `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token --hostname <host>`. Read-only use only. Enterprise orgs with single sign-on need an SSO-authorized token. perf-ratchet reads `DD_API_KEY`, `DD_APP_KEY`, `DD_SITE`, `PROMETHEUS_URL`, `PROMETHEUS_TOKEN`; Datadog keys go only to Datadog API hosts, and a POST goes only to the RUM aggregation query path.
- **Privacy:** run folders hold corporate data. They live outside the repo by default, and `.gitignore` blocks them inside it. Nothing is sent anywhere except GitHub API requests.
- **Model tokens:** Claude never reads raw responses or `metrics.json` in full; the digest is capped at 12,000 bytes and `budget.json` checks the run against `--max-tokens` (default 25,000). In chronicle, raw tool output stays inside the gatherer subagent.
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
uv run mypy plugins/chronicle/src/chronicle
claude plugin validate .                  # marketplace and plugin manifests
python3 <groundwork>/engine/groundwork.py verify   # all of the above
claude --plugin-dir plugins/impact-review # try the plugin in Claude Code
plugins/chronicle/scripts/chronicle build plugins/chronicle/examples/keystone/story.json --out /tmp/keystone
```
