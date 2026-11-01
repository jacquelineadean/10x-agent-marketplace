# Spec 002: chronicle split into four plugins on one engine

Source: [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md), revision 3. Built ahead of approval at the
owner's request (31 Oct 2026), as for RFC-0002 to RFC-0006.
Each acceptance criterion names the test that checks it or a manual check. The work lands as a stack of draft
pull requests, each based on the one before; the first is based on the RFC's own pull request.

| PR | Branch | Phase | Releases |
| --- | --- | --- | --- |
| 1a | `claude/rfc7-1-engine` | 1: engine extraction, Python side | chronicle 0.5.0 |
| 1b | `claude/rfc7-1b-assets` | 1: page parts, chrome registries, vocabulary lint | chronicle 0.5.1 |
| 2 | `claude/rfc7-2-sources` | 2: sources plugin, chronicle researcher | sources 0.1.0, chronicle 0.6.0 |
| 3 | `claude/rfc7-3-briefing` | 3: briefing, brand kit | briefing 0.1.0, chronicle 0.6.1 |
| 4 | `claude/rfc7-4-blueprint` | 4: blueprint, TAD move, interactive figures | blueprint 0.1.0, chronicle 0.7.0 |
| 5 | `claude/rfc7-5-collectors` | 5: script-lane collectors, refresh, uploads, impact-review on sources | sources 0.2.0, briefing 0.2.0, impact-review 0.2.0, blueprint 0.2.0, chronicle 0.7.1 |
| 6 | `claude/rfc7-6-creative` | 6: creative additions | chronicle 0.8.0 |

## Design decisions that refine the RFC
- **Registries.** `chronicle_engine.registry` holds block types, the art provider, page chrome (progress devices,
  chapter marks, stat skins, plate frames), animation kinds, theme policies, CLI commands and asset roots. A
  plugin's `pack` module fills them on import; its `__main__` imports the pack and runs the engine CLI.
- **The page layout stays in the engine** with neutral chrome: progress `steps`, marks `label`, `plain`, `step` and
  `none`, stats `rule` and `cards`, frame `none`, track lines `solid` and `dashed`. chronicle registers the
  creative chrome: progress `arches`, `track`, `route`, `tape`, `flags` and `clock`, track lines `belt`, `road` and
  `rail`, marks `arch`, `tag`, `sign`, `badge`, `flag`, stats `receipt` and `ticket`, frames `mat` and `tape`. A
  plugin's pack sets its defaults, so a chronicle page with no theme looks as it does today. The progress icons stay
  in the engine, because flow figures and widgets draw them too.
- **Art is a provider.** A story's `art`, `hero.art`, `chapters[].art` and the `plate` block need the art provider.
  chronicle registers the painter as that provider; another plugin's build refuses `art` with a message.
- **The SVG reader stays in chronicle.** Only the painter and the scene kind read drawings, so `parse.py` and
  `pathdata.py` stay beside the painter (the RFC's table listed them under the engine).
- **Page parts.** A page ships the engine's always-parts (base, page and neutral identity CSS; core, progress and
  boot scripts) plus the parts of each figure type on it: charts, figures (stats, scrolly, timeline, stepper,
  compare, matrix, roadmap, team, model), explainers (tilemap, flow, diagram), lessons (quiz, checklist, widget)
  and the drawn-figure CSS (diagram, plate). `14-page.css`, the page layout and the neutral figure styles, ships
  with every page: its rules use shared class names (`.seg`, `.card`, `.tile`, `.step`) that widgets may also
  render, so splitting it could change a widget's look. chronicle adds its chrome parts to every page and its plate
  parts to pages with art.
- **The split keeps the cascade.** CSS moved between files so the joined order stays the same, except where neutral
  and creative rules swapped places inside the identity stylesheet; those rules style different elements. Every
  element's computed style is compared between the 1a and 1b builds to prove it.
- **Stable output.** The diagram kind ordered its pulse tracks by Python's per-run string hashing, so the same
  animation could build to two different files. It now uses first-appearance order.
- **Tests.** Existing chronicle tests stay with chronicle, because they test chronicle's behavior through the
  engine. Engine-only tests live in `packages/chronicle-engine/tests/` with `test_engine_*.py` names.

## Acceptance criteria

### PR 1a: engine extraction (behavior unchanged)
| ID | Criterion | Check |
| --- | --- | --- |
| AC-1 | `packages/chronicle-engine/src/chronicle_engine/` holds facts, derive, the story model and renderer, theme tokens, the motion clock and stage, the diagram kind, the SVG reader, the files, browser and video connectors, and the engine CLI | `test_engine_boundary.py::test_engine_modules_exist` |
| AC-2 | `plugins/chronicle/src/chronicle_engine` is a symlink to that package, and a local marketplace install copies real files | `test_engine_boundary.py::test_chronicle_links_the_engine`; manual check M-1 |
| AC-3 | The engine imports no plugin package | `test_engine_boundary.py::test_engine_imports_no_plugin` |
| AC-4 | The engine CLI runs with no pack: `check` and `build` work for a story without art, and refuse `art` with a message | `test_engine_cli.py` |
| AC-5 | Every bundled example and the docs pages build byte-for-byte as before: 57 files compared at a fixed `PYTHONHASHSEED` (the 4 `publish-files.json` hold absolute paths), and the outputs no longer depend on the hash seed | build comparison recorded in the PR; `plugins/chronicle/tests/test_pack.py` |
| AC-6 | The sameness review runs only through chronicle's `distinct` policy | `plugins/chronicle/tests/test_theme.py` |
| AC-7 | The four quality gates pass; chronicle is 0.5.0 in both manifests | CI and `claude plugin validate .` |

### PR 1b: page parts and chrome registries
| ID | Criterion | Check |
| --- | --- | --- |
| AC-8 | The page runtime starts figures through a registry, so a page without a block's part still starts | `test_engine_pages.py` and browser check M-2 |
| AC-9 | A page ships only the CSS and script parts its blocks and chrome use | `test_engine_pages.py::test_parts_follow_blocks` |
| AC-10 | Creative chrome comes from chronicle's registrations; the engine alone offers the neutral chrome | `test_engine_pages.py::test_engine_chrome_is_neutral`, `plugins/chronicle/tests/test_theme.py` |
| AC-11 | No engine file uses a plugin word: watercolor, plate, sameness, KPI, SQL, Datadog | `test_engine_boundary.py::test_engine_vocabulary` |
| AC-12 | Every example page loads in Chromium with no script error and starts every figure | browser check M-2, recorded in the PR |
| AC-13 | Pages render as in 1a: the same markup outside the runtime, and the same computed style for every element and pseudo-element in seven browser modes, for the 4 example pages and 14 theme variants that use the chrome the examples leave out | browser check M-4, recorded in the PR |
| AC-14 | The four quality gates pass; chronicle is 0.5.1 in both manifests | CI and `claude plugin validate .` |

### PR 2: sources plugin and chronicle researcher
Design decisions:
- **Gatherer modes.** `sources:gatherer` takes `Mode: status` (the nine `detect` lines),
  `Mode: gather` (query, write `facts.json` and `queries.json`, run `sources digest`) and
  `Mode: digest` (after another agent wrote part of the files).
- **The picker.** `sources detect --picker` prints AskUserQuestion's `questions` argument.
  chronicle links no `packages/sources`, so `story` asks the gatherer for its status lines and
  builds the same three questions from them.
- **Lanes in 0.1.0.** The gatherer reads through the session's connectors only. Keys, programs
  and named connections show in `detect` and feed the script collectors of sources 0.2.0.
  The SQL and HTTPS guards arrive with those collectors in PR 5, the code they guard.
- **Facts files join.** `facts_file` names a file or a list; files join by top-level key and
  a key in two files stops the build. The gatherer writes one key per system to `facts.json`;
  the researcher writes `research/facts.json` under `research`; Claude's own notes go to
  `notes.json` when a gatherer runs. A record's `locator` shows on hover.
- **One facts reference.** `facts.md` moves into the engine
  (`src/chronicle_engine/references/facts.md`); chronicle reads it through its link, sources
  through a file link.
- **The database agent.** `sources agent` writes `~/.claude/agents/sources-db.md` from named
  connections: Postgres through `postgres-mcp --access-mode=restricted`, Oracle through
  SQLcl's `sql -mcp` with a saved connection, Databricks through the workspace's managed SQL
  server. Keys appear only as `${VARIABLE}` references. A page calls `sources-db`, then the
  gatherer's `Mode: digest`.
- **chronicle.** The researcher replaces `chronicle-gatherer`, and `references/sources.md`
  becomes the sources recipes. chronicle declares no dependency on sources.

| ID | Criterion | Check |
| --- | --- | --- |
| AC-15 | `sources detect` gives each of the nine systems a status from connectors, key names (never values), programs, named connections and the database agent | `test_sources_detect.py`, `test_sources_cli.py` |
| AC-16 | The picker is three multi-select questions (code and work, operations, data) of three systems each, every option described by its status | `test_sources_detect.py`, `test_sources_cli.py` |
| AC-17 | `sources check` refuses a fact with no query, a record whose source is not its system, a top-level key that is not a system and a bad queries entry; `digest` writes `digest.md` under 12,000 bytes only after the check passes | `test_sources_contract.py`, `test_sources_cli.py` |
| AC-18 | `connections.json` holds hosts and variable names; a value that is not a variable name is refused and never echoed | `test_sources_connections.py`, `test_sources_cli.py` |
| AC-19 | `sources agent` writes `sources-db` with one read-only server per database connection and no secret | `test_sources_cli.py::test_agent_writes_a_user_level_database_agent` |
| AC-20 | Every system has a recipe; `connect` is user-invoked only; the gatherer's description stays under 450 characters; no plugin bundles an MCP server; `packages/sources` imports no engine or plugin | `test_sources_plugin.py`, `test_sources_boundary.py` |
| AC-21 | A story joins facts files by top-level key and stops on a key in two files; a fact's locator shows on hover | `test_engine_facts.py` |
| AC-22 | The researcher replaces `chronicle-gatherer`; `chronicle research` refuses a fact without a locator and a material digest over 12,000 bytes or missing a section | `test_research.py`, `test_pack.py` |
| AC-23 | Existing pages render as in 1b: the same markup and CSS, and a runtime that differs only by the locator line | build comparison recorded in the PR |
| AC-24 | A local marketplace install caches sources' linked package and linked facts reference as real files | manual check M-5 |
| AC-25 | The quality gates pass, now with `mypy packages/sources/src/sources`; sources is 0.1.0 and chronicle 0.6.0 in both manifests | CI and `claude plugin validate .` |

### PR 3: briefing, layouts and the brand kit
Design decisions:
- **Layouts.** `registry.LAYOUTS` maps a name to a renderer; the engine ships `page`, its
  output unchanged. A story's `layout` picks one; `new --layout` writes its skeleton. A
  layout's stylesheet and script are the parts of the figure type `layout:<name>`.
- **Plugin checks and keys.** `registry.CHECKS` runs a plugin's checks after the engine's;
  `BLOCK_KEYS` lists keys a layout reads on any block (`build`, `span`, `slice`); `FILES`
  names block keys whose files the build reads (the animation block's `svg`).
- **Queries on hover.** With `queries.json` beside a story, each fact's query, or its
  group's, shows on hover. Stories without one build as before.
- **Brand kit in the engine.** `--brand run|repo|config|PATH` on `new`, `check` and `build`;
  `run` is the default and optional; `new` copies a named kit into the run folder.
- **Animations step.** An animation's root SVG carries `data-steps`, `data-end` and
  `data-duration`, so a deck plays one step per click and stops on the finished picture.
- **References in the engine.** `blocks.md` (tokens, formats, every neutral block) and
  `widgets.md` move into the engine beside `facts.md`; chronicle's `story-format.md` keeps
  the top level, chapters and the plate block.
- **Isolation in tests.** briefing's pack runs only in subprocesses in the test suite, so its
  registrations never meet chronicle's.
- **Versions.** chronicle 0.6.1, for the engine changes it links.

| ID | Criterion | Check |
| --- | --- | --- |
| AC-26 | A deck renders a cover, a slide per chapter and a sources slide; builds, notes, the overview and one animation step per click work by keys, buttons and swipes | `test_briefing_cli.py`; browser check M-2 |
| AC-27 | A dashboard sets each KPI's status by rule (on, near, off target), shows the as-of stamp, renders one copy per filter option and the query behind each number on hover | `test_briefing_rules.py`, `test_briefing_cli.py` |
| AC-28 | `check` errors on a KPI without a target, a direction or a numeric value, and on a sliced block with no filter or a missing fact; warns on a KPI without a query, a slide past 60 words, 4 blocks or 80 title characters, and facts over 7 days old | `test_briefing_rules.py` |
| AC-29 | `--brand` reads a kit from the run, the repo, the config folder or a path, fills the theme, copies on `new`, and warns on departures; a missing named kit is an error | `test_engine_brand.py`, `test_briefing_cli.py` |
| AC-30 | `export --to slides` and `--to dashboard` write formatted values, statuses and queries; `slides --png --pdf` writes a PNG per slide and a PDF with one page per slide | `test_briefing_cli.py`; manual check M-6 |
| AC-31 | The engine alone offers only the page layout; briefing pages ship briefing's parts and none of chronicle's | `test_engine_brand.py`, `test_briefing_cli.py` |
| AC-32 | chronicle's pages keep their markup and CSS, their runtime adds only the query lines, and each animation file adds only the three step attributes | build comparison recorded in the PR |
| AC-33 | Installing briefing from the marketplace installs sources too | manual check M-6 |
| AC-34 | The quality gates pass, now with `mypy plugins/briefing/src/briefing`; briefing is 0.1.0 and chronicle 0.6.1 in both manifests | CI and `claude plugin validate .` |

### PR 4: blueprint, the TAD move and interactive figures
Design decisions:
- **The TAD moves.** Its code, stylesheet, example, reference and tests move to blueprint.
  chronicle keeps the scene and diagram kinds and starts new animations as scenes. The
  overview's and the RFC map's TADs build with blueprint.
- **Packet styles move to the engine.** The diagram kind draws packets with the classes the
  TAD stylesheet styled; those four rules move to the engine's diagram stylesheet, so
  chronicle's diagrams and briefing's deck animation keep their packets.
- **Drawn kinds.** `sequence` and `erd` write a drawing from data and play it through the
  engine's diagram kind: its checks, timing, motion and sanitizer.
- **The architecture block** wraps a built SVG: parts open their details, numbered pins
  mark decisions, and a player seeks the clock to each step. Parts resolve under every
  kind's id prefix; `check` refuses a part or pin the SVG lacks.
- **The prototype layout** puts screens behind tabs; `cards` and `list` link screens, a
  device toggle sets the width, and `check` refuses a link to a missing screen.
- **Shared references and checks.** `animation-format.md` and `formats.md` move into the
  engine's references; the built-animation check moves to the engine for briefing and
  blueprint.
- **Schema reads.** `blueprint schema` turns a column export into an `erd` object; live reads
  through the script lane arrive in PR 5. Mermaid and C4 import, in the RFC's command table
  but in no phase, are not built.
- **Versions.** chronicle 0.7.0 (the TAD leaves), blueprint 0.1.0.

| ID | Criterion | Check |
| --- | --- | --- |
| AC-35 | The TAD lives in blueprint; chronicle offers `scene` and `diagram` and defaults to `scene` | `test_blueprint_tad.py`, `test_pack.py`, `test_animate.py` |
| AC-36 | Each TAD built with blueprint equals its PR 3 build less chronicle's scene stylesheet, and every element's computed style matches | build comparison and M-4 style comparison recorded in the PR |
| AC-37 | chronicle's diagram and scene animations equal their PR 3 builds less the TAD-only rules, with the same computed style | build comparison and M-4 style comparison recorded in the PR |
| AC-38 | A sequence draws a lifeline per participant, broken around labels, and an arrow per message (sync, async, reply, self); with no steps each message plays in turn | `test_blueprint_kinds.py` |
| AC-39 | An ERD draws each table and routes each relation through the gaps with a crow's foot or a bar; `schema` turns the example's export into its `erd` object | `test_blueprint_kinds.py`, `test_blueprint_cli.py` |
| AC-40 | The architecture block opens part details and pins and seeks each step; `check` refuses a part or pin the SVG lacks | `test_blueprint_cli.py`; browser check M-2 |
| AC-41 | The prototype's tabs, card and row links and device toggle work; `check` refuses a link to a missing screen | `test_blueprint_cli.py`; browser check M-2 |
| AC-42 | Every blueprint example checks clean and builds | `test_blueprint_cli.py` |
| AC-43 | Installing blueprint installs sources | manual check M-7 |
| AC-44 | The quality gates pass, now with `mypy plugins/blueprint/src/blueprint`; blueprint is 0.1.0 and chronicle 0.7.0 in both manifests | CI and `claude plugin validate .` |

### PR 5: script-lane collectors, refresh, uploads, impact-review on sources
Design decisions:
- **The script lane.** A `queries.json` entry with `"lane": "script"` carries a `request`
  in its system's recipe shape. `sources gather` runs each one: one value becomes a record
  (source, unit, and a note that ends with the window), any table one list per column, and
  the entry gets the query as run, the window read and its as-of date. One entry failing
  never stops the others; an entry that never ran is a warning, so the digest still lists
  what was read.
- **Nine collectors.** Every recipe promised a script collector in sources 0.2.0. Counting
  collectors count per period (`per`: day, week, month, quarter or year, at most 120) and
  ask each system for a total only: GitHub search and workflow runs, Jira, Confluence,
  PagerDuty (six months a call, longer windows month by month), ServiceNow's Aggregate API.
  Datadog reduces daily rollups per period in code, reads SLO history and computes RUM
  values per period in Datadog. Databricks runs statements and reads Unity Catalog lineage;
  Postgres and Oracle run through the user's `psql` and SQLcl.
- **Read-only POSTs.** The RFC names Datadog's RUM aggregate and Databricks statements. Jira
  Cloud counts issues only through `search/approximate-count`, so that path joins the list.
- **SQL guard and sessions.** Before any connection: one `SELECT` or `WITH`, no write
  keyword outside literals and quoted names, no side-effect function, no backslash, dollar
  or q-quoting, named parameters only. Postgres runs read-only with a 30-second statement
  timeout set through `PGOPTIONS` and returns JSON rows; Oracle runs in a `SET TRANSACTION
  READ ONLY` transaction under a 45-second process limit, its start-up plus the statement,
  because Oracle has no session statement timeout; Databricks waits 30 seconds, then
  cancels. Every SQL result stops at 10,000 rows.
- **Secrets.** Keys come from environment variables through a named connection or the
  system's defaults. Passwords travel in libpq's variables or on SQLcl's standard input,
  never in an argument list; messages name variables, never values.
- **Refresh.** `briefing refresh` runs the script lane again with each window moved to end
  with the last complete period (whole months stay whole months; other windows keep their
  days and end yesterday), then builds. `queries.json` records the date as `refreshed`; a
  fact whose entry is older shows "Not refreshed since" on hover and on its KPI tile, and the
  dashboard names those systems under its stamp. The engine copies each entry's as-of date
  onto its facts, so a tooltip shows the date of the read.
- **Uploads.** `export --to google|microsoft --file` writes `build/upload.json` with the
  question the user answers. Claude uploads through the user's connector only after a yes
  (amendment 1); code never uploads. The file is the .pptx the Slides type downloads or the
  printed PDF.
- **impact-review on sources.** Its GitHub transport, host endpoints, token lookup and errors
  move to `packages/sources/src/sources/connectors/github/`; it links the package and keeps
  its queries, parsing, cache and collection, passing its own User-Agent.
- **impact-review keeps its charts.** The RFC's phase 5 moves it onto the engine's charts.
  Those draw in the browser with scripts and web fonts, and impact-review's dashboard
  promises offline HTML with inline SVG and no scripts (its README and `test_outputs.py`).
  Moving needs the owner to drop that promise or a static chart renderer in the engine, so
  it is not built.
- **blueprint reads live.** `schema --connection` reads a Postgres catalog through
  `pg_catalog` (`information_schema` hides constraints from a role that may only SELECT) or
  an Oracle one through the `ALL_` views; `lineage` turns a table's Unity Catalog lineage
  into a TAD. Long column types shorten (`timestamptz`) or are cut to fit their row.
- **Versions.** sources 0.2.0, briefing 0.2.0, impact-review 0.2.0, blueprint 0.2.0 (new
  commands) and chronicle 0.7.1 (engine changes).

| ID | Criterion | Check |
| --- | --- | --- |
| AC-45 | The SQL guard passes one read-only statement and refuses writes, data-changing CTEs, `SELECT INTO`, row locks, side-effect functions, several statements, psql commands and unknown parameters | `test_sources_sql.py`; manual check M-8 |
| AC-46 | Every collector sends GET over HTTPS, or POST only to a named read-only path, and turns recorded replies into the expected values and per-period lists | `test_sources_collectors.py` |
| AC-47 | psql and SQLcl start from argument lists in read-only sessions with their time limits, and no password reaches an argument list | `test_sources_databases.py`; manual check M-8 |
| AC-48 | `gather` writes each result at its path, stamps its entry, reports failures apart and rolls windows to the last complete period | `test_sources_gather.py`, `test_sources_periods.py` |
| AC-49 | `detect` says "script collector ready" for a system with keys or a named connection and its program | `test_sources_detect.py` |
| AC-50 | `briefing refresh` reads the script lane again, rebuilds, and marks older facts on hover, on KPI tiles and under the dashboard's stamp | `test_briefing_refresh.py`, `test_engine_brand.py` |
| AC-51 | `export --to google` and `--to microsoft` write the upload manifest and its question, and refuse a file that is not a deck | `test_briefing_refresh.py`; the upload stays in manual check M-3 |
| AC-52 | impact-review links `packages/sources`, and its outputs and GitHub requests match PR 4's for six scopes | comparison recorded in the PR; `test_sources_boundary.py` |
| AC-53 | `blueprint schema --connection` reads keys and relations live; `lineage` writes a TAD that checks and builds | `test_blueprint_live.py`; manual check M-8 |
| AC-54 | chronicle's pages keep their markup and CSS; their runtime changes only by the as-of and stale tooltip lines | build comparison recorded in the PR |
| AC-55 | The quality gates pass; sources, briefing, impact-review and blueprint are 0.2.0 and chronicle 0.7.1 in both manifests | CI and `claude plugin validate .` |

### PR 6: creative additions
Design decisions:
- **Built from the reference pages.** Ossabaw (rigs, habitat, tour, house), ROK (game
  scoring) and Four Mental Models (pen notes) were read and their defects listed first;
  the blocks keep their mechanics and fix those defects: journals merge on every write and
  follow other tabs; the tide updates under reduced motion; a mirror turns about the foot
  point; actor depth stays above the painting; focus moves to the opened stop, room or
  result and pans to a tabbed animal; rooms are tabs with arrow keys; exits and stops are
  links without scripts; `phase` is in cycles for every role; full screen is the
  browser's own.
- **Rigs in drawings.** A `data-rig` group of `data-part` groups paints each part opaque on
  its own sheet; the manifest keeps each part's box, pivot and role numbers and the rig's
  gait, bob, foot, speed and stride. The page turns parts with the CSS `rotate` and
  `translate` properties; animations turn them with keyframes about the same pivot, with
  whole cycles in the loop. A `rig` animation kind plays a drawing's rigs with an
  optional gait; a scene's rigs play the same way.
- **One figure each, parts only where used.** Rigs, pen notes, holes, panoramas, rooms and
  tours are figures with their own script and style parts, so a page ships them only when
  it has them, and every page without them builds byte for byte as before. A painter
  change repaints each painting once (the manifest records a fingerprint of the painting
  code); the images come out the same.
- **Places reuse plates.** Each room, a tour's map and a tour's plate stops are plates, so
  layers, labels and the develop effect stay one implementation. A tour stop's scene is a
  `plate`, `rooms` or `panorama` block rendered by the same code as in a chapter.
- **Device records.** Holes, journals and tour visits live in the browser's storage under
  `chronicle-game:`, `chronicle-journal:` and `chronicle-tour:` keys, from the block's key
  or the page title. Blocked storage keeps them for the visit.
- **Game scoring** replaces the engine's quiz renderer only when the story has `game`;
  otherwise quizzes render as before.
- **Widget library.** `chronicle widgets list|add|save` keeps drills under the repository's
  `.chronicle/widgets/`, the user's config folder or the plugin's bundled `widgets/`, in
  that order; `save` runs the widget checks first.
- **Versions.** chronicle 0.8.0. The engine is unchanged.

| ID | Criterion | Check |
| --- | --- | --- |
| AC-56 | `widgets list`, `add` and `save` find drills in the repository, config and bundled roots in that order, copy them into a run with the block to paste, and refuse a script the widget checks fail | `test_widget_library.py` |
| AC-57 | Plate `notes` draw circle, underline, arrow, cross, tick and box marks in three pens, repeat for the same seed, write themselves after the plate develops, and the check names missing anchors, bad marks, bad pens and long words | `test_plate_notes.py`; manual check M-9 |
| AC-58 | With `game`, quizzes play as holes against par with strokes, names, a tally in the bar and a scorecard; without it a quiz renders as the engine's quiz | `test_game.py`; manual check M-9 |
| AC-59 | The SVG reader reads rigs, parts, roles, defaults, pivots and gaits, and refuses parts outside a rig, layers inside one, nested rigs, unknown gaits and roles, duplicates and malformed pivots | `test_rigs.py` |
| AC-60 | Rig parts paint opaque on their own sheets and the manifest keeps their pivots and the rig's settings; a plate shows a rig as one figure with each part about its pivot | `test_rigs.py`; manual check M-9 |
| AC-61 | Animations turn rig parts about their pivots on whole cycles; `kind: rig` plays a drawing's rigs with an optional gait and checks its art, gait and steps | `test_rigs.py`; manual check M-9 |
| AC-62 | `panorama` places animals by their foot point and scale, layers by role, zones, the tide slider and the fallback list, and its check names rigs, layers, behaviors, tides and journal keys | `test_places.py`; manual check M-9 |
| AC-63 | `rooms` renders tab panels with numbered details and doorways that link to their rooms, and its check names ids, art, anchors, targets and arrows | `test_places.py`; manual check M-9 |
| AC-64 | `tour` routes its stops on the map, opens their plate, rooms or panorama scenes, links back, onward and to the stop's chapter, and its check names stops, chapters, scenes and pins, including rooms inside stops | `test_places.py`; manual check M-9 |
| AC-65 | Pages without notes, rigs, holes, panoramas, rooms or tours ship none of their parts, and every example and variant builds byte for byte as in PR 5 except the art manifests' painter fingerprint | `test_rigs.py`, `test_plate_notes.py`, `test_places.py`; build comparison recorded in the PR |
| AC-66 | `examples/field-guide` checks clean, differs from every other example's theme, and loads with no script errors at desktop and phone widths and under reduced motion | `test_theme.py`; manual checks M-2 and M-9 |
| AC-67 | The quality gates pass; chronicle is 0.8.0 in both manifests | CI and `claude plugin validate .` |

### Review follow-up: subagent models and moved kinds
Design decisions:
- **Subagents on Sonnet.** `sources:gatherer`, `chronicle:researcher` and the `sources-db`
  agent that `sources agent` writes set `model: sonnet`, as impact-writer and perf-writer
  do. Without it they ran on the session's model. Their output passes through scripts
  (`sources digest`, `chronicle research`) that check it, and none of them does arithmetic.
- **Moved kinds name their plugin.** `registry.MOVED_KINDS` maps a kind a plugin no longer
  draws to the line that says where it went. chronicle registers `tad`, so a TAD written
  for chronicle 0.4 fails its check with "TADs moved to the blueprint plugin".
- **Versions.** Unchanged: chronicle 0.8.0, sources 0.2.0, briefing 0.2.0.

| ID | Criterion | Check |
| --- | --- | --- |
| AC-68 | The gatherer, the researcher and the written `sources-db` agent run on Sonnet | `test_sources_plugin.py`, `test_research.py`, `test_sources_cli.py` |
| AC-69 | `chronicle animate check` on a `tad` animation names blueprint and does not call the `tad` object unused | `test_animate.py` |
| AC-70 | `briefing slides` prints its errors to standard error; `briefing check` reads a `queries.json` that is not an object without a traceback | `test_briefing_cli.py` |

## Manual checks
- **M-1.** Install chronicle from a local marketplace into a scratch `CLAUDE_CONFIG_DIR` and confirm the cache holds
  `src/chronicle_engine/` as real files.
- **M-2.** Load every example page in headless Chromium at 1280 pixels; record script errors (none allowed) and the
  count of started figures.
- **M-3.** RFC-0007 phase 0 items that need other hosts: install on claude.ai, in Cowork and on a Windows checkout;
  run a user-level gatherer with inline `mcpServers`; create a file through the Google Drive and Microsoft 365
  connectors. These cannot run in the build container and stay open.
- **M-4.** Build every example and 14 quarterly variants (progress `arches`, `tape`, `flags`, `clock`; track lines
  `solid`, `road`, `rail`; marks `arch`, `sign`, `flag`, `step`, `none`; stats `rule`; frame `none`) with 1a and 1b
  at `PYTHONHASHSEED=11`. Compare the markup outside the runtime, then load each pair in Chromium with a frozen page
  clock in seven modes (desktop light, dark, attribute dark, reduced motion, forced colors; phone light and dark), at
  the top and the middle of the page, and compare the DOM and every computed style. Wall-clock motion (painted
  layers, flow tokens) is parked before each snapshot; a mode that differs is re-run three times.
- **M-5.** Install sources and chronicle from a local marketplace into a scratch
  `CLAUDE_CONFIG_DIR` and confirm the cache holds `src/sources/` and `references/facts.md` as
  real files, and chronicle's `agents/researcher.md` in place of `chronicle-gatherer.md`.
- **M-6.** Install briefing from a local marketplace into a scratch `CLAUDE_CONFIG_DIR` and
  confirm sources installs with it; print the keystone deck with `slides --png --pdf` and
  look at every page.
- **M-7.** Install blueprint from a local marketplace into a scratch `CLAUDE_CONFIG_DIR` and
  confirm sources installs with it and the TAD files land in blueprint's cache.
- **M-8.** Against a local Postgres 16 with a SELECT-only role: `sources gather` writes a
  table and two values; refuses more than 10,000 rows, a `DELETE` inside `WITH` and a psql
  backslash; the read-only session stops a function the guard passes that inserts; a
  35-second query stops at 30 seconds; `--roll` moves a quarter to the last complete month;
  `blueprint schema --connection` reads every key and relation as that role.
- **M-9.** Build `examples/field-guide` and drive it in Chromium at 1280 and 390 pixels and
  under reduced motion: open a tour stop (focus on its title), walk through a doorway
  (focus on the new room), go back to the map (focus on the stop left), pick a zone, move
  the tide (shore animals hide and show in both motion modes), pick an animal (journal
  count rises and survives a reload), press End on the view, play both holes and read the
  scorecard. Seek a `rig` animation to two times and compare the legs.
