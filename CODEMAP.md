# Code map — 10x-agent-marketplace

<!-- Maintained by hand. Update it in the same change that adds, moves or removes a folder. -->

Read this before searching the code: it says where each kind of code lives.

**Layout:** standard (cli profile, root plugins/impact-review/src/impact_review)
New code goes in its role folder; the import rules are in Notes.
**Languages:** Python (collector, tests), Markdown (skills, agents, prompts), JSON (manifests, fixtures)

## Folders

| Folder | Role | Code files | Holds |
| --- | --- | --- | --- |
| `plugins/impact-review/src/impact_review/core` | core | 13 | Pure rules: domain records (`models.py`), scope parsing (`scope.py`), timeframe parsing and year chunks, the `ActivitySource` port, metric rules (`metrics.py`, `cadence.py`, `highlights.py`, `themes.py`, `stats.py`), `report.py` (metrics.json shape), `digest.md` renderer with the 12 KB cap, dashboard and SVG charts, token budget |
| `plugins/impact-review/src/impact_review/connectors/github` | connectors | 4 | Every GitHub query impact-review makes: GraphQL documents, the `raw/` cache, payload parsing, and `GitHubSource` (scope member lookups, per-person collection with year chunking, paging and org filter); the transport, host endpoints, token lookup and errors come from the linked `sources/connectors/github/` |
| `plugins/impact-review/src/impact_review/entrypoints/cli` | entrypoints | 1 | `collect` command: flags, run folder, writes the seven output files, prints at most 15 lines, exit codes 0/1/2 |
| `plugins/impact-review/src/impact_review/config` | config | 1 | The only environment reads: `IMPACT_REVIEW_HOST`, `IMPACT_REVIEW_RUNS`, and the standard-library `.env` reader; token names live in the linked sources package |
| `plugins/impact-review/src/impact_review/prompts` | prompts | 0 | `rubric-individual.md` and `rubric-group.md`, the default five-area rubrics; the CLI copies one into each run folder as `rubric.md` |
| `plugins/impact-review/tests` | tests | 10 | pytest suite with a fake HTTP opener; `fixtures/` holds recorded GitHub responses |
| `plugins/impact-review/skills/report` | plugin | 0 | `SKILL.md` for `/impact-review:report` |
| `plugins/impact-review/agents` | plugin | 0 | `impact-writer.md`, the Sonnet subagent that writes the synthesis files |

## Outside systems (where they are called)

| System | Called from |
| --- | --- |
| GitHub GraphQL and REST APIs | `connectors/github/http.py` (transport), `connectors/github/source.py` (queries) |
| GitHub CLI (`gh auth token`) | `connectors/github/token.py` |

## Settings (where environment variables are read)

| Name | Read in |
| --- | --- |
| `GITHUB_TOKEN`, `GH_TOKEN` | `config/settings.py` (names), used by `connectors/github/token.py` |
| `IMPACT_REVIEW_HOST`, `IMPACT_REVIEW_RUNS` | `config/settings.py` |

Secrets: read from environment variables; locally from `.env` (git-ignored); names listed in `.env.example`.

## Entry and wiring files

- `plugins/impact-review/src/impact_review/__main__.py`: builds the GitHub connector and calls the CLI (`python -m impact_review`).
- `plugins/impact-review/src/impact_review/entrypoints/cli/main.py`: argument parsing and the `collect` command.

## Tests

- `plugins/impact-review/tests/`: `uv run pytest` from the repo root; `pyproject.toml` sets the test path and `pythonpath`.

## Notes

- `.github/` holds CI and release automation, outside the plugin code: `workflows/` (`ci.yml`, `pr-lint.yml`, `release.yml`, the reusable `release-please.yml`), `scripts/check-versions.sh`, `release-kit/` (files other repos copy), the PR template, issue forms, CODEOWNERS and `dependabot.yml`. RELEASING.md describes them.
- Import rules: `core` imports nothing outside itself; `connectors` and `entrypoints` import `core` and `config`; only `__main__.py` imports both `connectors` and `entrypoints`.
- The facts above describe `plugins/impact-review` only. chronicle's code lives in two places. The shared engine follows the cli layout under `packages/chronicle-engine/src/chronicle_engine/`, and each plugin that uses it links that folder into its own `src/`:

| Folder | Holds |
| --- | --- |
| `registry.py` | extension points plugins fill: block types, the art provider, page chrome (progress devices, chapter marks, stat skins, frames), page parts by figure type, layouts, checks, block keys and files, animation kinds, theme policies, commands, asset roots and defaults |
| `core/story/` | facts and tokens, derive table, story checks, theme tokens, fonts and contrast (`theme.py`), brand kits (`brand.py`), the diagram sanitizer, US tile grid (`geo.py`), HTML renderer with the page layout and the neutral block renderers (`blocks.py`, `explainers.py`, `lessons.py`, joined in `dispatch.py`) |
| `core/motion/` | animations: the shared checks and step clock (`model.py`), CSS keyframe timeline, stage (title, captions, step strip, the SVG file), the diagram kind, the packet and visibility parts, render, the HTML figure, frame times and the GIF encoder |
| `connectors/files/` | every file read and write: JSON, HTML, WebP, bundled assets joined across the engine's and plugins' asset roots |
| `connectors/browser/` | an installed headless Chromium or Chrome: page screenshots (`shoot.py`), animation frames, slide images and PDFs over the DevTools pipe (`devtools.py`) |
| `connectors/video/` | MP4 through the installed ffmpeg program, WebM through OpenCV's video writer |
| `entrypoints/cli/` | the command line a plugin runs after its pack registers: new, check, paint (with an art provider), build, shoot (`main.py`), `animate new/check/build` (`animate.py`), run folders and joined facts files (`runs.py`) |
| `references/` | what every plugin's skills read through their link: the facts file (`facts.md`), blocks, tokens and formats (`blocks.md`), widgets (`widgets.md`), the animation file (`animation-format.md`) and export formats (`formats.md`) |
| `config/` | the only environment reads: the user's brand kit folder |
| `assets/` | `fonts.json`; `css/` the page stylesheet in numbered parts; `js/` the page runtime in numbered parts, each figure starting through the `INIT` table; a page ships the parts its figures use, joined inside one IIFE; `motion/` the stage and diagram stylesheets |
| `packages/chronicle-engine/tests/` | engine-only tests run with no plugin: the boundary and vocabulary lint (`test_engine_boundary.py`), the command line (`test_engine_cli.py`), page parts and neutral chrome (`test_engine_pages.py`), joined facts files and locators (`test_engine_facts.py`), shared helpers (`engine_helpers.py`) |

chronicle's own code lives under `plugins/chronicle/src/chronicle/`:

| Folder | Holds |
| --- | --- |
| `pack.py` | chronicle's registrations: the painter as art provider, the `plate`, `panorama`, `rooms`, `tour` and `scorecard` blocks and their parts, quizzes as holes, the page chrome, the scene and rig kinds, the `distinct` policy, the `motifs`, `research` and `widgets` commands, defaults |
| `core/story/` | plates on the page with pen notes and rigs (`plates.py`), the panorama, rooms and tour blocks (`panorama.py`, `rooms.py`, `tour.py`), game scoring (`game.py`), ids and device storage keys (`keys.py`), the notes check (`checks.py`), the widget library's format (`library.py`), the creative page chrome and its parts (`chrome.py`), the sameness review (`review.py`) and the checks on the researcher's files (`research.py`) |
| `core/watercolor/` | painting engine (paper, washes, ink), motifs, presets and the scene language |
| `core/watercolor/svg/` | SVG drawings: path and transform math (`pathdata.py`), the reader with layers, anchors and rigs (`parse.py`) and the ink-and-wash painter (`paint.py`) |
| `core/motion/` | the scene kind and the rig gaits it and the rig kind play (`scene.py`) |
| `entrypoints/cli/` | painting shared by build, paint and animate (`art.py`), the `motifs` and `research` commands (`commands.py`), the widget library command (`widgets.py`) |
| `assets/` | chronicle's page and animation parts: `css/11-plates.css`, `css/12-game.css`, `css/13-arch-mark.css`, `css/15-rigs.css`, `css/16-notes.css`, `css/17-panorama.css`, `css/18-rooms.css`, `css/19-tour.css`, `css/21-identity-devices.css`, `js/30-plates.js`, `js/31-notes.js`, `js/32-game.js`, `js/33-rigs.js`, `js/34-panorama.js`, `js/35-rooms.js`, `js/36-tour.js`, `js/41-devices.js` (progress devices), `motion/30-scene.css` |
| `plugins/chronicle/examples/` | worked examples with invented data: `keystone/` (status page), `onboarding/` (handbook with a widget), `quarterly/`, `field-guide/` (tour, rooms, panorama with rigs, notes, holes), and the animations `animation-diagram/` and `animation-scene/` |
| `plugins/chronicle/widgets/` | the bundled widget library: `order-drill/`, `match-drill/`, `sort-drill/`, `flash-drill/`, each a `widget.js`, `widget.css` and `widget.json` |
| `plugins/chronicle/tests/` | pytest suite, run from the repo root with `uv run pytest` |

blueprint's code lives under `plugins/blueprint/src/blueprint/`, beside links to the engine and to `packages/sources`:

| Folder | Holds |
| --- | --- |
| `pack.py` | blueprint's registrations: the tad, sequence and erd kinds, the architecture, cards, list and solutions blocks, the prototype layout, their page parts, checks and the schema, lineage, solutions and sources commands |
| `core/tad/` | technical architecture diagrams (moved from chronicle): spec reader, tier and lane layout, line routing, icons, the drawing with its motion, and the kind (`kind.py`) |
| `core/` | kinds drawn as diagrams (`drawn.py`, `sequence.py`, `erd.py`), the architecture block (`architecture.py`), the prototype layout with cards and lists (`prototype.py`), checks (`checks.py`), schema rows and the catalog queries for ERDs (`schema.py`), Unity Catalog lineage as a TAD (`lineage.py`) |
| `core/solutions/` | the solution visualizer, no I/O: formulas read into trees and evaluated (`formula.py`), the solutions file's checks and plain form (`spec.py`), results per scenario and swings per control (`simulate.py`), the results as facts and `digest.md` with the 12 KB cap (`digest.py`), the exported decision's check and `decision.md` (`decision.py`), the block's HTML (`block.py`) |
| `entrypoints/cli/` | the check that reads animation files beside the story, `schema` (CSV or a live read through the sources collectors), `lineage`, `solutions` with `new`, `simulate` and `decide` (`solutions.py`), and the linked `sources` command |
| `assets/` | the architecture, cards and lists, prototype and solutions stylesheets and scripts (`css/63-solutions.css`; `js/84-solutions-model.js` walks the formula trees, `js/85-solutions.js` draws the controls, `js/86-solutions-feel.js` plays waits and failures); `motion/20-tad.css` |
| `plugins/blueprint/skills/` | `architecture/`, `prototype/` and `solution-visualizer/`, each a `SKILL.md` with `references/` |
| `plugins/blueprint/agents/` | `solution-scout.md`, the Haiku subagent that reads a repository into `context.md` or `locate.md` |
| `plugins/blueprint/examples/` | `animation-tad/`, `checkout-sequence/`, `orders-erd/`, `checkout-architecture/`, `oncall-prototype/`, `catalog-solutions/` |
| `plugins/blueprint/tests/` | `test_blueprint_*.py` with `blueprint_helpers.py`; TAD tests register the kind per test, builds run in their own process, and `test_blueprint_solutions.py` drives the built page in a local Chromium |

briefing's code lives under `plugins/briefing/src/briefing/`, beside links to the engine and to `packages/sources`:

| Folder | Holds |
| --- | --- |
| `pack.py` | briefing's registrations: the deck and dashboard layouts, the kpi, filters and animation blocks, their page parts, block keys, checks and the export, slides, refresh and sources commands |
| `core/` | the deck and dashboard layouts (`deck.py`, `dashboard.py`), KPI tiles and status rules (`kpi.py`), filters and slices (`slices.py`), the animation block (`animation.py`), checks (`checks.py`), Slides and Dashboard content (`export.py`), the Google and Microsoft upload manifest (`upload.py`) |
| `entrypoints/cli/` | the check that reads files beside the story, `export`, `slides` (PNG and PDF through Chromium), `refresh` (gather with rolled windows, then build) and the linked `sources` command |
| `assets/` | the deck, KPI and filter, dashboard and animation stylesheets and scripts |
| `plugins/briefing/examples/` | `keystone-deck/` and `keystone-dashboard/`, on the Keystone example's facts |
| `plugins/briefing/tests/` | `test_briefing_*.py` with `briefing_helpers.py`; builds run in their own process |

sources' code follows the same layout under `packages/sources/src/sources/`, linked into `plugins/sources/src/sources`:

| Folder | Holds |
| --- | --- |
| `core/` | the nine systems and picker groups (`systems.py`), detection (`detect.py`), the AskUserQuestion picker (`picker.py`), named connections (`connections.py`), the facts and queries contract (`contract.py`), `digest.md` (`digest.py`), the user-level database agent (`agent.py`), periods and rolled windows (`periods.py`), the SQL guard (`sql.py`), where a collector reads (`reach.py`), results and request checks (`collect.py`), the gather bookkeeping (`gather.py`) |
| `connectors/` | the HTTPS transport (`http.py`) and errors, one script-lane collector per system (`atlassian.py`, `datadog.py`, `pagerduty.py`, `servicenow.py`, `databricks.py`, `postgres.py` through psql, `oracle.py` through SQLcl), the collector table (`collectors.py`) and `wire.py`, the network and programs a collector touches |
| `connectors/github/` | the GitHub transport, host endpoints, token lookup and errors (moved from impact-review, which links them) and the search and workflow-run counts (`counts.py`) |
| `connectors/files/` | JSON and Markdown reads and writes |
| `connectors/system/` | which programs are on `PATH` |
| `entrypoints/cli/` | the `sources` command: detect, gather (`gather.py`), check, digest, connection, agent, and the same command as a host plugin exposes it (`linked.py`) |
| `config/` | the only environment reads: the environment for collectors, which key names are set, the connections file, Claude's user folder |
| `packages/sources/tests/` | `test_sources_*.py` with `sources_helpers.py` (recorded replies, fake psql and SQLcl); `fixtures/` holds a recorded reply per collector; no test calls a system |
| `plugins/sources/` | the plugin shell: `agents/gatherer.md`, `skills/connect/`, `recipes/` (one per system), `references/facts.md` (a link to the engine's), `scripts/sources`, `tests/` |

speedup follows the same cli layout under `plugins/speedup/src/speedup/`:

| Folder | Holds |
| --- | --- |
| `core/` | domain records (`model.py`), project file checks (`project.py`), daily bucketing, imports and change records (`records.py`), statistics (`stats.py`), journey, change and benchmark analysis (`analysis.py`), the ratchet (`ratchet.py`), `metrics.json` (`report.py`), digest with the 12 KB cap, token budget, number formats, SVG charts, dashboard, Markdown renderer, write-up tokens (`writeup.py`), the `SeriesSource` port |
| `connectors/http.py` | the one JSON transport: https only, retries, read-only POST allowlist, no secrets in logs |
| `connectors/datadog/` | Datadog sites and the metric and RUM queries |
| `connectors/prometheus/` | Prometheus range queries |
| `connectors/bench/` | runs benchmark commands as argument lists and parses their numbers |
| `connectors/files/` | project file, change log and the data folder |
| `entrypoints/cli/` | the `speedup` command: init, measure, import, bench, guard, tighten, log, report, writeup |
| `config/` | the only environment reads: Datadog keys and site, Prometheus, runs folder, project file path |
| `prompts/` | `writeup-outline.md`, the write-up's sections and voice |
| `plugins/speedup/examples/` | `demo/` (invented Lumen project, imports and a sample write-up), `github-actions/` (guard and tighten workflow) |
| `plugins/speedup/tests/` | pytest suite with recorded Datadog and Prometheus responses in `fixtures/` |

tokenwise follows the same cli layout under `plugins/tokenwise/src/tokenwise/`:

| Folder | Holds |
| --- | --- |
| `core/` | domain records (`model.py`), transcript parsing (`transcript.py`), weighted usage (`usage.py`), per-session rules (`session_rules.py`), cross-session and project rules with merge and rank (`project_rules.py`), settings fixes and undo (`fixes.py`), the loop guard (`guard.py`), handoff facts (`handoff.py`), `metrics.json` and the 12 KB digest (`report.py`) |
| `connectors/files/` | every file read and write: transcripts and subagent transcripts (read-only), instruction file sizes, `.mcp.json`, JSON writes, the data folder |
| `entrypoints/cli/` | the `tokenwise` command: audit, apply, undo, handoff (`main.py`), shared audit and apply steps (`actions.py`), the Claude Code hooks (`hooks.py`) |
| `config/` | the only environment reads: runs folder, auto-apply switch, Claude config folder |
| `plugins/tokenwise/hooks/` | `hooks.json`: Stop, PostToolUse and PostToolUseFailure on Bash, PreCompact |
| `plugins/tokenwise/tests/` | pytest suite; `fixtures/` holds transcript lines in the shape Claude Code writes |

contributing has no code, only skills:

| Folder | Holds |
| --- | --- |
| `plugins/contributing/skills/pull-request/` | `SKILL.md` for PR titles and descriptions; `references/` holds the default PR template, GitHub advanced formatting and the Playwright screenshot and recording guide |
| `plugins/contributing/skills/branch-and-commit/` | `SKILL.md` for branch names, Conventional Commit messages, commit shaping and safe rewrites |
