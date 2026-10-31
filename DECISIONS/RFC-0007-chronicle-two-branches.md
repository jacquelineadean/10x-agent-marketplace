---
id: RFC-0007
title: "chronicle in two branches: creative pages and data briefings on one engine"
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude Code session, 31 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006]
author: Claude Code, for Jacqueline Dean
created: 2026-10-31
---

# RFC-0007 chronicle in two branches: creative pages and data briefings on one engine

## 1. Summary
chronicle 0.4 serves two kinds of work through one `story` skill and one `animation` skill.
Creative work wants a painted identity that no other page shares.
Business work wants numbers from company systems, the house brand on every page, and a refresh button.
This RFC proposes one shared engine with two plugins on top of it:

1. **chronicle-engine** (`packages/chronicle-engine/`): facts, derive, the document model, the block registry, the renderer, theme tokens, the motion clock and every export. It names neither branch.
2. **chronicle 0.5** (creative): `story` and `animation` for illustrated pages and painted animations. It owns the watercolor painter, plates, scenes, identity devices and the sameness review.
3. **briefing 0.1** (data; working name): `deck`, `dashboard`, `architecture` and `prototype`. It owns KPI rules, slide and dashboard layouts, TADs, the brand kit, the collectors and the gatherer subagent.

Each plugin reaches the engine through a symlink in its `src/` folder.
Claude Code copies linked files into its plugin cache at install, so each plugin installs alone and git holds one copy.
Integrations run only in scripts and subagents, so neither plugin adds an MCP server to a session.

Status: proposal for discussion. Nothing is built.
`docs/rfc-0007-map/` holds an interactive map of this proposal with the open questions pinned to the parts they change.

## 2. The need
**User scenario:** Jacqueline Dean asked to "bifurcate the chronicle plugin story and animation skills" into
"creative, illustrative usages and technical/business usages", "without duplicating functionality or bloating
context window with unrelated integrations/logic", with each branch's functionality kept "without impacting the other".

| | Creative and illustrative | Technical and business |
| --- | --- | --- |
| Examples | Ossabaw Island tour, Four Mental Models podcast companion, ROK Yardage Book handbook | KPI dashboards, executive overviews, slide-style decks, system design visuals, data-driven prototypes |
| Identity | unique per page, taken from the subject's world | the organization's brand, the same on every page |
| Data | pasted notes, files, transcripts, public sources | GitHub, Datadog, Jira, Confluence, Databricks, Postgres, Oracle, ServiceNow, PagerDuty |
| Lifetime | built once | rebuilt each week or meeting |
| Craft | paintings, rigged animals, map tours, games | numbers with targets, a query behind every number |

Evidence, measured on commit `b356522`:
- One description serves both uses. `story`'s 810-character description lists portfolio and incident reviews beside podcast guides and handbooks. `animation`'s 648 characters list TADs beside painted scenes.
- Each run loads the other branch's guidance. A dashboard request reads `identity.md` (14.5 KB) and `illustration.md` (9.4 KB): about 6,000 tokens of painting advice. A field guide reads `sources.md`, which teaches GitHub, Jira and Datadog queries.
- `claude plugin details` puts chronicle at about 605 tokens in every session: `story` 280, `animation` 230, `chronicle-gatherer` 90. Invoking `story` adds about 3,800 tokens and `animation` about 2,000, before any reference file.
- The theme engine has one policy. `chronicle check` warns when a page shares three of six features with another page. A team's decks should share all six.
- The three reference pages needed code chronicle lacks, and none of it touches a data source. Ossabaw (462 KB, 120 images) ships four widgets (tour, house, habitat three times, nest) and 18 rigged animals. ROK added about 1,000 hand-written lines. Four Mental Models was written outside chronicle.
- Business pages need nine or more integrations. Bundled as plugin MCP servers, each would add its instructions and tool names to every chronicle session.
- Chart and dashboard code already exists three times: impact-review (`charts.py`, `dashboard.py`), speedup (`charts.py` 202 lines, `dashboard.py` 658) and chronicle (`10-charts.js`, 31 KB). HTTPS transports exist twice: impact-review 180 lines, speedup 161.

**Done means** (for the build that follows approval):
- A creative-only install carries no data skill, agent, recipe or MCP server.
- A data-only install carries no painter, identity reference or creative skill.
- One `facts.json` builds as a painted story in chronicle and as a deck and a dashboard in briefing.
- Each branch keeps golden examples and trigger evals, and both run on every engine change.
- No engine file uses a branch's vocabulary.
- The four quality gates pass.

## 3. Interview record
No interview was held. The request named the two uses, the creative examples and the data sources.
The other answers are proposals and stay open in section 10.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | What splits? | The story and animation skills, by use | From request |
| 2 | Creative references | Ossabaw tour, podcast companion, ROK gamified handbook | From request; the uploaded builds were read for section 2 |
| 3 | Data outputs | System design visuals, KPI dashboards, executive overviews, slide decks, prototypes | From request |
| 4 | Data sources | GitHub, Datadog, Jira, Confluence, Databricks, Postgres, Oracle, ServiceNow, PagerDuty | From request |
| 5 | Packaging | Two plugins over one linked engine | Proposed, open (10.1) |
| 6 | Data plugin name | `briefing` | Proposed, open (10.2) |
| 7 | Company data in creative pages | Through briefing's gatherer when installed | Proposed, open (10.3) |

## 4. Proposal

### 4.1 The rule that routes a request
The requested treatment picks the branch: illustration goes to chronicle, data-first output goes to briefing.
A status report can land in either one.

| Request | Branch | Skill |
| --- | --- | --- |
| "An illustrated field guide to Ossabaw Island" | creative | `chronicle:story` |
| "A companion page for this podcast episode" | creative | `chronicle:story` |
| "A gamified handbook for new staff" | creative | `chronicle:story` |
| "A painted scene of the outage for the all-hands" | creative | `chronicle:animation` |
| "A watercolor status story for the steering committee" | creative, with gathered facts | `chronicle:story`, facts from `briefing:gatherer` |
| "A Q3 KPI dashboard from Datadog and Jira" | data | `briefing:dashboard` |
| "An executive overview of the migration" | data | `briefing:dashboard` |
| "Slides for Thursday's architecture review" | data | `briefing:deck` |
| "Animate how a checkout request crosses our services" | data | `briefing:architecture` |
| "A clickable on-call prototype with real PagerDuty numbers" | data | `briefing:prototype` |

An ambiguous request goes to briefing, which needs no painter and loads fewer tokens.
chronicle takes it when the request asks for illustration, watercolor, a story, a guide, a tour or a game.
Each skill description names the requests that belong to the other plugin.

### 4.2 Layers
```
                 chronicle (creative)                       briefing (data)
 skills          story · animation                          deck · dashboard · architecture · prototype
 agents          none                                       gatherer (MCP lane)
 plugin code     watercolor painter, plates, scenes,        KPI and target rules, deck, dashboard and
                 identity devices, sameness review,         prototype layouts, TAD, sequence, ERD,
                 rigs, panoramas, tours, game scoring       lineage, brand kit, refresh, digest
 references      identity, illustration, editorial voice,   brand, KPIs, deck, one recipe per source,
                 guide and handbook outlines                status, review and incident outlines
 ──────────────── chronicle-engine: one folder in git, linked into both plugins ─────────────────
                 facts, derive, tokens · document model, block registry, page renderer
                 theme tokens, fonts, contrast · motion clock, stage, diagram kind, exports
                 files, browser and video connectors · shared format references
 ──────────────── sources: one folder in git, linked into briefing only ────────────────────────
                 HTTPS transport · SQL and HTTP read-only guards · collectors · recorded fixtures
```

### 4.3 The engine
Today's code splits along these lines (lines of Python unless marked):

| Today | Size | Goes to |
| --- | --- | --- |
| `core/story`: facts, derive, model, markup, html, render, dispatch, diagram sanitizer | 2,904 with `theme.py` | engine |
| 19 neutral blocks: prose, stats, quote, chart, scrolly, timeline, stepper, compare, matrix, roadmap, team, model, table, flow, tilemap, diagram, quiz, checklist, widget | in `blocks.py`, `explainers.py`, `lessons.py` | engine |
| Theme tokens, fonts, dark palette, contrast raise | part of `theme.py` (628) | engine |
| Identity devices (route, tape, arches, flags and clock progress; chapter marks; receipt and ticket stats; surface; words) and the sameness review | rest of `theme.py`; `20-identity.css` 13 KB; `40-progress.js` 18 KB | chronicle |
| Watercolor painter, presets, motifs, ink-and-wash | 3,205 | chronicle |
| SVG reader (`parse.py`, `pathdata.py`), used by `motion/render.py` | 841 | engine |
| `plate` block and `30-plates.js` | 5 KB of script | chronicle |
| Motion clock, stage, parts, embed, frames, GIF; `diagram` kind | 1,663 | engine |
| `scene` kind | 444 | chronicle |
| `tad` kind | 1,706 | briefing |
| Files, browser and video connectors; CLI commands | 1,263 | engine |
| `chronicle-gatherer`, `sources.md` | 4.5 KB of text | briefing |
| `identity.md`, `illustration.md` | 23.9 KB | chronicle |
| `story-format.md`, `facts.md`, `widgets.md`, `animation-format.md`, `formats.md` | 27.7 KB | engine references, read through each plugin's link |
| `outlines.md`, `voice.md` | 6.9 KB | split by chapter plan and voice |
| Examples keystone, onboarding, quarterly, animation-scene | | chronicle |
| Examples animation-tad, animation-diagram; `docs/chronicle-overview` | | briefing |

The engine ends near 6,400 lines of Python and 150 KB of CSS and script.
chronicle keeps about 4,000 lines; briefing starts with the 1,706 TAD lines.

**Registries.** The engine exposes six registries, and each plugin's entry point fills them before a command runs:

| Registry | Engine ships | chronicle adds | briefing adds |
| --- | --- | --- | --- |
| Blocks | the 19 neutral blocks | plate, panorama, tour, rooms, game scoring | kpi, filters |
| Layouts | page | none | deck, dashboard, prototype |
| Animation kinds | diagram | scene, rig | tad, sequence, erd, lineage |
| Theme policies | tokens only | distinct (the sameness review) | brand (the brand kit check) |
| Checks | tokens, unsourced numbers, sanitizer, widget lint | concept present, paintings exist | KPI has target and query, stale facts, slide text fits |
| Commands | new, check, build, shoot, animate | paint, motifs | gather, refresh, digest, schema |

A part moves into the engine when a second plugin needs it.
So the deck layout starts in briefing and moves when chronicle wants a painted talk deck.

**Import rule.** The engine imports no plugin code. Each plugin imports the engine.
Plugins never import each other: an install holds only its own code and the engine, so a cross import fails at once.
A test walks the imports and fails earlier, in this repo.

**Page weight.** Each block registers its CSS and script parts, and a page ships only the parts its blocks use (RFC-0004 9.1).
A dashboard then skips 13 KB of identity CSS and 18 KB of progress devices.

### 4.4 Sharing the engine between plugins
A spike with Claude Code 2.1.316 on 31 Oct 2026 measured three facts:
- A plugin whose `src/engine` is a symlink to `../../../packages/engine/src/engine` installed from a marketplace folder. The cache held the linked files as real files.
- `claude plugin validate` passed that plugin with no warning about the link.
- `"dependencies": ["alpha"]` in beta's `plugin.json` made `claude plugin install beta` install alpha too ("+ 1 dependency: alpha").

| Option | How | Cost |
| --- | --- | --- |
| A. Linked engine (proposed) | `plugins/<name>/src/chronicle_engine` links to `packages/chronicle-engine/src/chronicle_engine` | one copy in git; claude.ai, Cowork and Windows checkouts still need a test |
| B. Generated copies | a script copies the engine into each plugin; a test fails when copies differ | two committed copies of 6,400 lines |
| C. One plugin, two skill families | both families stay in `plugins/chronicle` | no linking; every user pays for six descriptions; one version for both; strains principle 5 |
| D. Engine plugin as a dependency | both plugins declare `"dependencies": ["chronicle-engine"]` | install works; no variable points at another plugin's files, and a `bin/` on PATH is refused by claude.ai and Cowork |

Recommendation: A. Option C is the fallback if claude.ai or Cowork rejects the link.
The Claude Code docs say `${CLAUDE_PLUGIN_ROOT}` is always the plugin's own root, and the cache path changes with each version.

### 4.5 Data access with no context cost in the main conversation
Code costs no context until something reads it. Claude Code charges context at five points:

| Point | When it is paid | Design |
| --- | --- | --- |
| Skill and agent descriptions | every session | short descriptions; setup skills set `disable-model-invocation: true`, which drops their description from the listing |
| `SKILL.md` body | each invocation | one workflow per skill, under 5 KB |
| References | each read | per-branch files; the gatherer reads one recipe per source it queries |
| MCP servers | every session where the plugin is enabled: server instructions and tool names | no MCP servers in either `plugin.json` |
| Tool output | each call | raw responses stay in scripts or the gatherer; Claude reads `digest.md` (12 KB cap) |

Three documented limits shape this design:
- The skill listing gets 1% of the context window. Past it, Claude Code drops descriptions, and routing gets worse.
- Plugin agents ignore `mcpServers`. No plugin setting can start a server inside the gatherer only.
- The saving holds per session. A project that enables both plugins pays both listings. `enabledPlugins` in a project's `.claude/settings.json` turns each plugin on where it is used.

Two lanes write one contract.
- **Script lane (collectors).** `briefing gather` runs read-only queries with keys from environment variables and writes facts. Standard-library HTTPS covers GitHub, Datadog, Jira, Confluence, PagerDuty, ServiceNow (Table and Aggregate APIs) and Databricks (SQL Statement Execution and Unity Catalog lineage). Postgres runs through the user's `psql` and Oracle through SQLcl, both as argument lists. No model reads a raw row.
- **MCP lane (gatherer subagent).** It serves claude.ai, Cowork, and users with connectors and no keys. The subagent queries the session's connectors, writes facts and replies in at most 10 lines, as `chronicle-gatherer` does today. For a database server the user does not want in every session, `/briefing:connect` can write a user-level agent to `~/.claude/agents/`. User-level agents honor inline `mcpServers`, so that server starts only inside the subagent (open question 10.5).

Both lanes write three files to the run folder:
- `facts.json`: every value with its source, as today.
- `queries.json`: the query behind each fact, its connection alias, window, lane and as-of date.
- `digest.md`: fact keys, last values and series summaries under 12 KB, for Claude to read.

`briefing refresh` replays the script-lane queries and rebuilds the page with no model call.
Facts from the MCP lane show as stale until the gatherer runs again.

Guards live in code:
- SQL: one statement, `SELECT` or `WITH` only, named parameters, a read-only session, a 30-second timeout and a 10,000-row cap. Postgres sets `default_transaction_read_only`; Oracle runs `SET TRANSACTION READ ONLY`; Databricks uses a read-only principal. Recipes push aggregation into SQL.
- HTTPS: GET only, plus named read-only POST paths: Datadog's RUM aggregate (as in speedup) and Databricks statement execution behind the SQL guard.
- Secrets: environment variables only. `connections.json` holds hosts and variable names. No log line holds a header.
- Text from tools is data. Every recipe repeats the gatherer's rule against following it.

`packages/sources` starts from speedup's `connectors/http.py` and Datadog source and from impact-review's GitHub connector.
It imports neither the engine nor a plugin, so speedup and impact-review can link it later (phase 5).

### 4.6 chronicle 0.5: the creative plugin
chronicle keeps `story`, `animation` (scene and diagram), the painter, plates, identity, the sameness review, quizzes, checklists and widgets.
It hands briefing the TAD kind, the gatherer, `sources.md` and the status, review and incident outlines.
With `briefing:gatherer` in the session, `story` delegates company facts to it; without it, `story` extracts facts from pasted content and files.
chronicle declares no dependency on briefing: a dependency installs and enables briefing, which would load its listing into every creative session.

It gains the parts the three reference pages built by hand (RFC-0004 section 9):

| Addition | Built by hand in | What it does |
| --- | --- | --- |
| rigs | Ossabaw, 18 species | drawings split into parts with pivots, painted per part, with walk, graze, root, swim and crawl gaits |
| `panorama` block | Ossabaw habitat, used three times | a wide painted habitat to drag across: zones, tide and surf overlays, animals with field cards and a journal |
| `tour` block | Ossabaw tour | a painted map hub whose stops open scenes, walked by a route progress device |
| `rooms` block | Ossabaw house | paintings with numbered details and doorways between rooms |
| game scoring | ROK, about 700 lines of script | quizzes played as holes, a tally that colors the progress device, a closing scorecard, drills |
| plate notes | Four Mental Models | red-pen marks that appear as the reader arrives |
| widget library | Ossabaw's `tools/widgets.py` | a drill written once and reused across runs |
| rig animations | new | `animation` plays a rig's gait as SVG, GIF or MP4 |

Description sketch, about 330 characters: "Illustrated, interactive story pages and painted animations whose look comes from the subject: field guides and tours, podcast, talk and book companions, gamified handbooks and training, illustrated status stories. Watercolor paintings, rigged animals, maps and games. For KPI dashboards, slide decks or architecture diagrams, use briefing."

### 4.7 briefing 0.1: the data plugin

| Skill | Makes | Built on |
| --- | --- | --- |
| `deck` | slide-style HTML presentations: one idea per slide, builds, speaker notes, a presenter view with timer, an overview grid, one URL hash per slide, PDF through Chromium's print, a PNG per slide | engine renderer; an embedded animation advances one step per click by seeking the one clock (RFC-0005 4.3) |
| `dashboard` | KPI dashboards and executive overviews: tiles with value, target, change and sparkline; status set by rule in code; filters over precomputed slices; tables; an as-of stamp; the query behind each number on hover | derive table, `queries.json`, `refresh` |
| `architecture` | system and data design visuals, still or animated: TAD (moved from chronicle), sequence diagrams (RFC-0005 9.4), ERDs from schema reads, Unity Catalog lineage, Mermaid and C4 import (RFC-0005 9.5) | engine motion and exports |
| `prototype` | clickable screens fed by facts: tabs, cards, lists, tables and charts, with widgets for behavior | engine renderer and widget contract |

- **Agent:** `gatherer`, the MCP lane.
- **User-invoked skill:** `connect` writes `connections.json` and lists the environment variables to set. It sets `disable-model-invocation: true`, so its description stays out of every session and it never triggers from a request.
- **Brand kit:** `brand.json` holds the palette, fonts and a logo as SVG path data. It adds chart series checked for color-vision deficiency, a slide master (title, section, closing) and a footer label such as "Internal". `check` warns when a page departs from the kit. The sameness review is off, because a team's decks should look alike.
- **Voice:** the decision first, each KPI with its target and period, each risk with an owner.
- **Exports:** pages, decks and dashboards build with the standard library. PNG, GIF and MP4 keep NumPy and OpenCV (pending RFC-0002).

### 4.8 Keeping each branch intact
Six gates run on every change, so a change in one branch cannot alter the other unseen:
1. **Import boundary.** A test fails when the engine imports plugin code or one plugin imports the other.
2. **Golden builds.** pytest builds chronicle's onboarding, quarterly, keystone and animation-scene. It builds briefing's deck, dashboard and TAD from keystone's `facts.json`.
3. **Branch checks on those builds.** chronicle examples pass the sameness review and paint. briefing examples pass the brand check, carry a query for every KPI, and build pages with neither NumPy nor OpenCV installed.
4. **Trigger evals** with `claude plugin eval`: 15 prompts per branch and 10 ambiguous ones. Each must load the expected skill and no skill from the other plugin.
5. **Vocabulary lint.** Engine files may not contain branch words such as watercolor, plate, sameness, KPI, SQL or Datadog. RFC-0004 found the base stylesheet calling the accent "the new platform"; this lint catches that leak.
6. **Versions.** An engine change bumps both plugins. A plugin change bumps only that plugin.

### 4.9 Context budget
Targets are estimates for the spec to confirm with `claude plugin details`.

| Item | chronicle 0.4 today | chronicle 0.5 target | briefing 0.1 target |
| --- | --- | --- | --- |
| Always-on tokens | about 605 | about 400 | about 450 |
| Skill body per invocation | story 3,800; animation 2,000 | story 3,000; animation 1,800 | about 1,200 per skill |
| References a typical run reads | up to 52.9 KB (story) | about 40 KB | about 15 KB |
| MCP servers in the main conversation | 0 | 0 | 0 |
| Source recipes loaded | `sources.md` on every story run | none | one per queried source, inside the gatherer |

### 4.10 Phases
Each phase gets a spec under `specs/` before code.

| Phase | Change | Release |
| --- | --- | --- |
| 0 | Install a plugin with a linked folder on claude.ai, Cowork and a Windows checkout; run one database through a user-level gatherer with inline `mcpServers` | none |
| 1 | Carve the engine inside chronicle with no behavior change: registries, per-block assets, import test, vocabulary lint; move it to `packages/chronicle-engine` and link it | chronicle 0.5.0 |
| 2 | Create briefing: move TAD, gatherer and data outlines; add `dashboard` and `deck`; narrow chronicle's descriptions; add trigger evals | briefing 0.1.0, chronicle 0.6.0 |
| 3 | Script lane: `packages/sources` with GitHub, Datadog and Jira, then PagerDuty, Confluence, ServiceNow, Databricks, Postgres and Oracle; `queries.json`, `refresh`, `digest` | briefing 0.2.0 |
| 4 | Creative additions: rigs, panorama, tour, rooms, game scoring, plate notes, widget library | chronicle 0.7.0 |
| 5 | Optional: speedup and impact-review link `packages/sources` and the engine's charts | their next minor versions |

## 5. Alternatives considered
- **A `mode` field in one skill.** Rejected: one `SKILL.md` would teach both workflows, so every run pays for both.
- **Two skill families in one plugin (option C).** Kept as the fallback. It needs no link. It costs every user six descriptions, ties both branches to one version and strains principle 5.
- **Two plugins with copied engines and no sync.** Rejected: 6,400 lines would drift, and AGENTS.md rule 1 forbids copied blocks.
- **An engine plugin as a dependency (option D).** Rejected for now: a script cannot find another plugin's files without a documented path.
- **MCP servers bundled in briefing's `plugin.json`.** Rejected: they start in every session where briefing is enabled, with their instructions and tool names. Plugin agents ignore `mcpServers`, so the plugin cannot confine a server to the gatherer.
- **Existing skills for dashboards and decks** (`data:build-dashboard`, `anthropic-skills:pptx`). Rejected: neither reads chronicle's facts file, derive table or brand kit, so numbers lose their sources.

## 6. Risks and objections
- **Links may fail** on claude.ai, Cowork or Windows checkouts with `core.symlinks=false`. Phase 0 tests all three; option C is the fallback.
- **Mis-routing** between the plugins. Trigger evals gate each release, and each description names the other plugin's requests.
- **Two installs** for users who want both. The marketplace README gives both commands, and chronicle works alone.
- **Both plugins on in one project** pay both listings, about 850 tokens. The README shows `enabledPlugins` per project.
- **Creative pages with company data** need briefing installed. `story` says so when the gatherer is missing.
- **Database access** carries the most risk. The SQL guard, read-only sessions, timeouts and row caps run in code. Recipes ask for aggregates. Nothing leaves the machine except a publish the user confirms.
- **Engine changes need both branches green.** The 103 chronicle tests run in one command today; the split adds briefing's suite to the same command.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only.
New: `packages/chronicle-engine/`, `packages/sources/`, `plugins/briefing/`.
Changed: `plugins/chronicle/`, `.claude-plugin/marketplace.json`, `pyproject.toml` test and source paths, `CODEMAP.md`, `ARCHITECTURE.md`, and the `PROJECT.md` glossary (engine, branch, layout, brand kit, collector, recipe, queries file).

**Constitution check:**
- Principle 1 (scripts compute, Claude writes): improves. The script lane aggregates in code and SQL, so no model reads raw data. The MCP lane keeps RFC-0002's open question 3.
- Principle 2 (every number has a source): extended. `queries.json` records the query behind each number, and `refresh` replays it.
- Principle 3 (local and private): kept. Collectors call only the system being read, and publishing stays user-confirmed.
- Principle 4 (read-only): enforced in code by the SQL guard and the HTTPS allowlist.
- Principle 5 (one plugin, one job): improves. chronicle paints stories and briefing presents data. The engine is a shared library with no manifest or skills.
- Guardrail on runtime dependencies: none added. Collectors use the standard library and the user's own `psql` and SQLcl.

## 8. Cross-repo contract
N/A, internal. Between the plugins the contract is files (`facts.json`, `queries.json`, `digest.md`) and the gatherer's agent name.

## 9. Out of scope
- Writing to any source system.
- Scheduled refresh; a later RFC could use scheduled tasks.
- PPTX export; decks print to PDF and PNG per slide.
- Bundling the three uploaded pages as examples. They stay outside the repo, and the evals use briefs that describe them.

## 10. Open questions
1. Approve two plugins over one linked engine (A), or two skill families in one plugin (C)?
2. Name the data plugin: `briefing`, `blueprint` or another name?
3. Should chronicle reach company data only through briefing's gatherer, or keep its own?
4. Which three sources come first? Proposed: GitHub and Datadog, whose code exists, and Jira.
5. Databases through the script lane only, or also through a user-level gatherer that `/briefing:connect` writes with inline `mcpServers`?
6. Deck exports: HTML, PDF and PNG, or PPTX as well?
7. Dashboards: plain pages as today, or claude.ai's Dashboard artifact type where an account offers it?
8. Where does the brand kit live: the user's repo, the run folder or a config folder?
9. Phase 5: should speedup and impact-review move onto the shared sources and charts?
10. Keystone: keep it as chronicle's painted status story, rebuild it as briefing's first deck, or both from one facts file?
