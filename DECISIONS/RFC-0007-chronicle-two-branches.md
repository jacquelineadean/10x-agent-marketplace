---
id: RFC-0007
title: "chronicle in branches: creative stories, data briefings and system blueprints on one engine"
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude Code session, 31 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006]
author: Claude Code, for Jacqueline Dean
created: 2026-10-31
revision: 3, with the owner's answers to all sixteen questions (31 Oct 2026)
---

# RFC-0007 chronicle in branches: creative stories, data briefings and system blueprints on one engine

## 1. Summary
chronicle 0.4 serves two kinds of work through one `story` skill and one `animation` skill.
Creative work wants a painted identity that no other page shares.
Business and technical work wants numbers from company systems, the house brand on every page, and a refresh button.
This RFC proposes one shared engine with four plugins on top of it:

1. **chronicle-engine** (`packages/chronicle-engine/`): facts, derive, the document model, the block registry, the renderer, theme tokens and the brand policy, the motion clock and every export. It names no plugin.
2. **chronicle** (creative): `story` and `animation`, plus a `researcher` subagent that turns provided material into facts. It owns the watercolor painter, plates, scenes, identity devices and the sameness review.
3. **briefing** (presentations): `deck` and `dashboard`, for horizontal slide decks, KPI dashboards and executive overviews.
4. **blueprint** (systems): `architecture` and `prototype`, for interactive system and data design visuals and data-driven prototypes.
5. **sources** (data access): the `gatherer` subagent, read-only collectors, source detection and `/sources:connect`. briefing and blueprint depend on it; chronicle borrows it when it is enabled.

Each plugin reaches the engine through a symlink in its `src/` folder; sources, briefing and blueprint also link the collectors.
Claude Code copies linked files into its plugin cache at install, so each plugin installs alone and git holds one copy.
Integrations run only in scripts and subagents, so no plugin adds an MCP server to a session.

Status: draft, revision 3. The owner answered all sixteen questions on 31 Oct 2026, and section 3 records them.
No question stays open. The RFC awaits approval with `/groundwork-specflow:approve`; nothing is built.
Answer 14 approved a constitution amendment, applied as amendment 1 in `CONSTITUTION.md` 1.1.0.
Answer 16 named speedup's successor; RFC-0008 covers that rename.
`docs/rfc-0007-map/` holds an interactive map of revision 1.

## 2. The need
**User scenario:** the request asked to split chronicle's story and animation skills into two uses: creative and
illustrative work, and technical and business work. It asked for no duplicated functionality, no unrelated
integrations or logic in the context window, and each branch's functions kept without changing the other.

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
- A creative-only install carries no data skill, recipe or MCP server.
- A briefing or blueprint install carries no painter, identity reference or creative skill.
- One `facts.json` builds as a painted story in chronicle and as a deck and a dashboard in briefing.
- Each plugin keeps golden examples and trigger evals, and all of them run on every engine change.
- No engine file uses a plugin's vocabulary.
- The four quality gates pass.

## 3. Interview record
Revision 1 took four answers from the request: what splits (the story and animation skills, by use), the creative
references, the data outputs and the nine data sources. The owner answered its ten open questions on 31 Oct 2026.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | Packaging | Two plugins over one linked engine; asked whether the engine should be an MCP server | Linked engine kept; 4.4 weighs the MCP form (10.1) |
| 2 | Data plugin name | Both names: `briefing` for decks and dashboards, `blueprint` for architecture visuals and prototypes | Three front-door plugins plus `sources` (4.5 to 4.8) |
| 3 | Company data in creative pages | Borrow the gatherer when installed; also work alone, perhaps with a new gatherer for provided material and tools | `chronicle:researcher` proposed in 4.6 (10.2) |
| 4 | First three sources | Dynamic, from the session and the request; with none given, ask the user to pick each source | Detection and a source picker (4.5) |
| 5 | Database access | An optional user-level gatherer with MCP servers | `/sources:connect --agent` (4.5) |
| 6 | Deck exports | Horizontal HTML slides, or Google and Microsoft servers that build the deck there | `deck` targets (4.7); external targets need an amendment (7, 10.4) |
| 7 | Dashboards | Plain pages by default, claude.ai's Dashboard type as an option | `--to dashboard` (4.7) |
| 8 | Brand kit location | All three places, chosen by flags, with the run folder as the default | `--brand` (4.3, 10.5) |
| 9 | speedup and impact-review | impact-review moves onto the shared sources and charts; speedup stays separate under a technical name | Phase 5; a separate rename RFC (10.6) |
| 10 | Keystone example | Both, from one facts file | Golden builds (4.9) |

Revision 2 asked six more questions, and the owner answered them on 31 Oct 2026.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 11 | Engine form | The linked library and CLI; an opt-in `chronicle-mcp` plugin only for shell-less hosts or MCP Apps | 4.4 |
| 12 | Gatherers | chronicle's `researcher` for provided material, plus `sources:gatherer` when enabled | 4.6 |
| 13 | Data-access plugin name | `sources` | 4.5 |
| 14 | External deck targets | Approve the principle 3 amendment; ship `--to slides` before the Google and Microsoft connectors | `CONSTITUTION.md` amendment 1; phases 3 and 5 |
| 15 | Brand kit paths | `.brand/brand.json` in the repo and `~/.config/chronicle/brand.json` for the config folder | 4.3 |
| 16 | speedup's new name | `perf-optimizer` | RFC-0008 |

## 4. Proposal

### 4.1 The rule that routes a request
The requested output picks the plugin.
Illustration goes to chronicle, numbers to present go to briefing, and a system's structure goes to blueprint.

| Request | Skill |
| --- | --- |
| "An illustrated field guide to Ossabaw Island" | `chronicle:story` |
| "A companion page for this podcast episode" | `chronicle:story` |
| "A gamified handbook for new staff" | `chronicle:story` |
| "A painted scene of the outage for the all-hands" | `chronicle:animation` |
| "A watercolor status story for the steering committee" | `chronicle:story`, with facts from `sources:gatherer` |
| "A Q3 KPI dashboard from Datadog and Jira" | `briefing:dashboard` |
| "An executive overview of the migration" | `briefing:dashboard` |
| "Slides for Thursday's quarterly review" | `briefing:deck` |
| "Animate how a checkout request crosses our services" | `blueprint:architecture` |
| "An ERD of the orders schema" | `blueprint:architecture` |
| "A clickable on-call prototype with real PagerDuty numbers" | `blueprint:prototype` |

An ambiguous request goes to briefing, which needs no painter and loads fewer tokens.
chronicle takes it when the request asks for illustration, watercolor, a story, a guide, a tour or a game.
Each skill description names the requests that belong to the other plugins.
A deck shows a blueprint animation by file: blueprint writes the SVG, and the deck's animation block plays it.

### 4.2 Layers
```
             chronicle             briefing             blueprint              sources
 skills      story, animation      deck, dashboard      architecture,          connect (you run it)
                                                        prototype
 agents      researcher            none                 none                   gatherer
 own code    painter, plates,      deck and dashboard   TAD, sequence, ERD,    detection, recipes,
             scenes, identity,     layouts, KPI rules   lineage, prototype     connections
             sameness review,                           screens
             rigs, tours, games
 ─────────── chronicle-engine: one folder in git, linked into chronicle, briefing and blueprint ───────────
             facts, derive, tokens · document model, block registry, renderer · theme tokens, brand policy
             motion clock, stage, diagram kind, exports · files, browser and video connectors
 ─────────── packages/sources: one folder in git, linked into sources, briefing and blueprint ────────────
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
| `tad` kind | 1,706 | blueprint |
| Files, browser and video connectors; CLI commands | 1,263 | engine |
| `chronicle-gatherer` | 1.8 KB of text | becomes chronicle's `researcher` (4.6) |
| `sources.md` | 2.7 KB of text | sources, as one recipe per system |
| `identity.md`, `illustration.md` | 23.9 KB | chronicle |
| `story-format.md`, `facts.md`, `widgets.md`, `animation-format.md`, `formats.md` | 27.7 KB | engine references, read through each plugin's link |
| `outlines.md`, `voice.md` | 6.9 KB | split by chapter plan and voice |
| Examples keystone, onboarding, quarterly, animation-scene | | chronicle |
| Examples animation-tad, animation-diagram; `docs/chronicle-overview` | | blueprint |

The engine ends near 6,400 lines of Python and 150 KB of CSS and script.
chronicle keeps about 4,000 lines; blueprint starts with the 1,706 TAD lines.

**Registries.** The engine exposes six registries, and each plugin's entry point fills them before a command runs:

| Registry | Engine ships | chronicle adds | briefing adds | blueprint adds |
| --- | --- | --- | --- | --- |
| Blocks | the 19 neutral blocks | plate, panorama, tour, rooms, game scoring | kpi, filters | part details, step player |
| Layouts | page | none | deck, dashboard | prototype |
| Animation kinds | diagram | scene, rig | none | tad, sequence, erd, lineage |
| Theme policies | tokens; brand (the brand kit check) | distinct (the sameness review) | none | none |
| Checks | tokens, unsourced numbers, sanitizer, widget lint, brand kit | concept present, paintings exist | KPI has target and query, stale facts, slide text fits | parts named, layout not shrunk below 62 percent |
| Commands | new, check, build, shoot, animate | paint, motifs | refresh, digest | schema, import |

A part moves into the engine when a second plugin needs it.
The brand policy moves now, because briefing and blueprint both use it.
The deck layout starts in briefing and moves when chronicle wants a painted talk deck.

**Brand kit (answers 8 and 15).** `--brand run|repo|config|PATH` picks the kit; `run` is the default.

| Flag value | File |
| --- | --- |
| `run` (default) | `<run folder>/brand.json` |
| `repo` | `<git root>/.brand/brand.json` |
| `config` | `$XDG_CONFIG_HOME/chronicle/brand.json`, else `~/.config/chronicle/brand.json` |
| a path | that file |

`new --brand repo|config|PATH` copies the kit into the run folder, so each run keeps the kit it was built with.
`build --brand` overrides the kit for one build. `check` warns when a page departs from the kit.

**Import rule.** The engine imports no plugin code. Each plugin imports the engine.
Plugins never import each other: an install holds only its own code and its links, so a cross import fails at once.
A test walks the imports and fails earlier, in this repo.

**Page weight.** Each block registers its CSS and script parts, and a page ships only the parts its blocks use (RFC-0004 9.1).
A dashboard then skips 13 KB of identity CSS and 18 KB of progress devices.

### 4.4 Sharing the engine, and whether it should be an MCP server
A spike with Claude Code 2.1.316 on 31 Oct 2026 measured three facts:
- A plugin whose `src/engine` is a symlink to `../../../packages/engine/src/engine` installed from a marketplace folder. The cache held the linked files as real files.
- `claude plugin validate` passed that plugin with no warning about the link.
- `"dependencies": ["alpha"]` in beta's `plugin.json` made `claude plugin install beta` install alpha too ("+ 1 dependency: alpha").

The Claude Code docs add two more: `${CLAUDE_PLUGIN_ROOT}` is always the plugin's own root, and the cache path changes with each version.
So no plugin can find another plugin's files at run time, and code sharing happens at install through links.

Answer 1 chose the linked engine and asked whether the engine should stand alone as an MCP server.

| Engine form | How a plugin reaches it | Always-on cost | Where it runs | Main cost |
| --- | --- | --- | --- | --- |
| Linked library and CLI (decided) | each plugin's launcher runs its linked copy through Bash | 0 tokens | Claude Code, and Cowork with a shell | every installer must keep the link |
| Versioned package | the launcher runs `uv run --with chronicle-engine==0.5.0` | 0 tokens | anywhere uv runs | a publish step per release; the first run downloads it |
| Local MCP server | a plugin's `.mcp.json` starts it, and skills call its tools | server instructions and tool names in every session where the plugin is enabled | Claude Code, Claude desktop, Cowork | a Python process in every such session, used or not; a 3-minute frame capture must finish inside one tool call; plugin agents cannot confine it to a subagent |
| Remote MCP server | a hosted endpoint | as above | claude.ai on the web as well | a hosted service that holds company data, against principle 3 and outside PROJECT.md's scope |

Decision (answer 11): keep the linked library and CLI.
The engine turns files into files, and Bash runs it at no context cost.
Two future needs would justify an MCP form, shipped as an opt-in `chronicle-mcp` plugin that users enable only where needed:
- a host with no shell, such as a claude.ai chat, needs to build pages;
- pages should render inline in a chat as MCP Apps, the interactive views an MCP tool can return.
The versioned package is the fallback if links fail on claude.ai, Cowork or Windows.

### 4.5 sources: data access as its own plugin
- **Why a plugin.** briefing and blueprint both need the gatherer, and an agent lives in exactly one plugin. Putting it in briefing would make blueprint depend on briefing and load briefing's skills in every blueprint session.
- **Dependencies.** briefing and blueprint declare `"dependencies": ["sources"]`, which installs and enables sources with them. chronicle declares none: a dependency would load the data listing into every creative session.
- **Always-on cost.** The gatherer's description, about 90 tokens. `connect` sets `disable-model-invocation: true`, which keeps its description out of the listing.
- **Code.** `packages/sources` is linked into sources, briefing and blueprint, so `briefing refresh` replays queries in-process.

Code costs no context until something reads it. Claude Code charges context at five points:

| Point | When it is paid | Design |
| --- | --- | --- |
| Skill and agent descriptions | every session | short descriptions; setup skills are user-invoked only |
| `SKILL.md` body | each invocation | one workflow per skill, under 5 KB |
| References | each read | per-plugin files; the gatherer reads one recipe per source it queries |
| MCP servers | every session where the plugin is enabled: server instructions and tool names | no MCP servers in any `plugin.json` |
| Tool output | each call | raw responses stay in scripts or subagents; Claude reads `digest.md` (12 KB cap) |

Three documented limits shape this design:
- The skill listing gets 1% of the context window. Past it, Claude Code drops descriptions, and routing gets worse.
- Plugin agents ignore `mcpServers`. No plugin setting can start a server inside the gatherer only.
- The saving holds per session. A project that enables every plugin pays every listing. `enabledPlugins` in a project's `.claude/settings.json` turns each plugin on where it is used.

**Choosing sources (answer 4).**
1. The skill reads the systems named in the request, the brief and any pasted links.
2. `sources detect` reports which systems have keys set, which programs are installed (`gh`, `psql`, `sql`, `databricks`) and which connections `connections.json` names. Claude adds the MCP connectors present in the session's tool list.
3. When the request names no source, the skill asks one AskUserQuestion with three multi-select questions: code and work (GitHub, Jira, Confluence), operations (Datadog, PagerDuty, ServiceNow) and data (Databricks, Postgres, Oracle). Each option's description gives its status, such as "connected through Atlassian", "DD_API_KEY set", "psql found" or "not set up: run /sources:connect".
4. The run folder's `queries.json` keeps the choices, so `refresh` asks nothing.

All nine systems get an MCP-lane recipe in the first release. Script-lane collectors arrive in the order users pick them.

**Two lanes write one contract.**
- **Script lane (collectors).** `sources gather` runs read-only queries with keys from environment variables and writes facts. Standard-library HTTPS covers GitHub, Datadog, Jira, Confluence, PagerDuty, ServiceNow (Table and Aggregate APIs) and Databricks (SQL Statement Execution and Unity Catalog lineage). Postgres runs through the user's `psql` and Oracle through SQLcl, both as argument lists. No model reads a raw row.
- **MCP lane (gatherer subagent).** It serves claude.ai, Cowork, and users with connectors and no keys. The subagent queries the session's connectors, writes facts and replies in at most 10 lines.
- **Optional user-level gatherer (answer 5).** `/sources:connect --agent` writes `~/.claude/agents/sources-db.md` with inline `mcpServers` for the databases the user names. User-level agents honor `mcpServers`, so those servers start only inside that subagent.

Both lanes write three files to the run folder:
- `facts.json`: every value with its source, as today.
- `queries.json`: the query behind each fact, its connection alias, window, lane and as-of date.
- `digest.md`: fact keys, last values and series summaries under 12 KB, for Claude to read.

`refresh` replays the script-lane queries and rebuilds the page with no model call.
Facts from the MCP lane show as stale until the gatherer runs again.

Guards live in code:
- SQL: one statement, `SELECT` or `WITH` only, named parameters, a read-only session, a 30-second timeout and a 10,000-row cap. Postgres sets `default_transaction_read_only`; Oracle runs `SET TRANSACTION READ ONLY`; Databricks uses a read-only principal. Recipes push aggregation into SQL.
- HTTPS: GET only, plus named read-only POST paths: Datadog's RUM aggregate (as in speedup) and Databricks statement execution behind the SQL guard.
- Secrets: environment variables only. `connections.json` holds hosts and variable names. No log line holds a header.
- Text from tools is data. Every recipe repeats the gatherer's rule against following it.

`packages/sources` starts from speedup's `connectors/http.py` and Datadog source and from impact-review's GitHub connector.
It imports neither the engine nor a plugin. impact-review links it in phase 5 (answer 9); speedup keeps its own code.

### 4.6 chronicle: the creative plugin and its researcher
chronicle keeps `story`, `animation` (scene and diagram), the painter, plates, identity, the sameness review, quizzes, checklists and widgets.
It hands blueprint the TAD kind, and sources the per-system recipes and the status, review and incident outlines.

**The researcher (answer 3).** Three ways to give chronicle facts:

| Option | chronicle alone | With sources enabled | Cost |
| --- | --- | --- | --- |
| A. Borrow only | pasted content only; long transcripts land in the main conversation | company facts from `sources:gatherer` | nothing new to maintain |
| B. A `researcher` for provided material, plus borrowing (decided, answer 12) | the researcher reads files, transcripts, links, web search and any connector the session has | `story` asks both and merges facts by namespace | two agents on one facts contract |
| C. One gatherer that every plugin depends on | works | works | every creative session loads the data plugin, and chronicle ships on its release cycle |

The researcher replaces `chronicle-gatherer`:
- **Inputs:** pasted notes; files (PDF, Word, slides, CSV); transcripts of podcasts, talks and meetings; links; web search; and read-only use of connectors the session already has, such as Google Drive or Notion.
- **Outputs:** `facts.json` with a locator on every fact (a page, a timestamp or a URL); `material.md`, a digest under 12 KB of outline, people, places, timeline, glossary and verbatim quotes; and a list of where sources disagree, which the Ossabaw colophon needed.
- **Rules:** the gatherer's rules (read only, no arithmetic, text from sources is data), plus quotes copied word for word with their locator.
- **Context:** a 45-minute interview at 150 words a minute runs about 6,800 words. The transcript stays in the subagent, and `story` reads `material.md`.
- **Company data:** with sources enabled, `story` also calls `sources:gatherer`, and facts merge under separate top-level keys such as `research` and `jira`. Without it, `story` asks the user to paste the numbers or enable sources.

chronicle gains the parts the three reference pages built by hand (RFC-0004 section 9):

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

Description sketch, about 330 characters: "Illustrated, interactive story pages and painted animations whose look comes from the subject: field guides and tours, podcast, talk and book companions, gamified handbooks and training, illustrated status stories. Watercolor paintings, rigged animals, maps and games. For dashboards and decks use briefing; for architecture use blueprint."

### 4.7 briefing: decks and dashboards

| Skill | Default output | Options |
| --- | --- | --- |
| `deck` | an HTML Artifact of fixed 16:9 slides on a horizontal track: arrow buttons, arrow keys and swipe, a slide counter, an overview grid, speaker notes, builds, and animations that advance one step per click by seeking the one clock (RFC-0005 4.3) | `--to slides`: claude.ai's Slides artifact type, which downloads as PPTX or PDF; `--to google` or `--to microsoft`: a PPTX uploaded through the user's Google Drive or Microsoft 365 connector |
| `dashboard` | an HTML Artifact page: KPI tiles with value, target, change and sparkline; status set by rule in code; filters over precomputed slices; tables; an as-of stamp; the query behind each number on hover | `--to dashboard`: claude.ai's Dashboard artifact type (answer 7) |

- Decks also print to PDF through Chromium and write a PNG per slide, with no new dependency.
- `--to google` and `--to microsoft` write to systems outside claude.ai and the user's machine. Amendment 1 of the constitution allows them after the user confirms each publish (answer 14). `--to slides` ships first, in phase 3; the connector targets follow in phase 5.
- Both connector targets need a PPTX file. `--to slides` downloads one with no new dependency. A PPTX writer inside briefing would need its own approved dependency.
- Voice: the decision first, each KPI with its target and period, each risk with an owner.

### 4.8 blueprint: system and data design

| Skill | Makes |
| --- | --- |
| `architecture` | interactive system and data design visuals, still or animated: TAD (moved from chronicle), sequence diagrams (RFC-0005 9.4), ERDs from schema reads, Unity Catalog lineage, Mermaid and C4 import (RFC-0005 9.5); parts open their details, pins mark decisions, a player steps through flows |
| `prototype` | clickable data-driven screens: tabs, cards, lists, tables and charts fed by facts, with widgets for behavior |

- Schema and lineage reads use `packages/sources`: `information_schema` through `psql` or SQLcl, and the Databricks lineage API. Both read metadata only.
- The map in `docs/rfc-0007-map/` is a working prototype of `architecture`'s interactive output: pins, part details and a step player around a chronicle TAD.

### 4.9 Keeping each plugin intact
Six gates run on every change, so a change in one plugin cannot alter another unseen:
1. **Import boundary.** A test fails when the engine imports plugin code or one plugin imports another.
2. **Golden builds.** pytest builds chronicle's onboarding, quarterly, keystone story and animation-scene; briefing's keystone deck and dashboard from keystone's `facts.json` (answer 10); blueprint's checkout TAD and the RFC-0007 map; and each collector against recorded fixtures.
3. **Plugin checks on those builds.** chronicle examples pass the sameness review and paint. briefing and blueprint examples pass the brand check, carry a query for every KPI, and build pages with neither NumPy nor OpenCV installed.
4. **Trigger evals** with `claude plugin eval`: 15 prompts per plugin and 10 ambiguous ones. Each must load the expected skill and no skill from another plugin.
5. **Vocabulary lint.** Engine files may not contain plugin words such as watercolor, plate, sameness, KPI, SQL or Datadog. RFC-0004 found the base stylesheet calling the accent "the new platform"; this lint catches that leak.
6. **Versions.** An engine change bumps every plugin that links it. A plugin change bumps only that plugin.

### 4.10 Context budget
Targets are estimates for the spec to confirm with `claude plugin details`.
That command still counts a `disable-model-invocation` skill (about 80 tokens in the spike), which the docs say stays out of the listing.

| Plugins enabled in a project | Always-on tokens today | Target |
| --- | --- | --- |
| chronicle alone | about 605 | about 470: two narrower skills and the researcher |
| briefing with sources | none today | about 390: two skills and the gatherer |
| blueprint with sources | none today | about 390: two skills and the gatherer |
| all four | none today | about 1,150 |

| Per run | Today | Target |
| --- | --- | --- |
| Skill body | story 3,800; animation 2,000 | about 3,000 for `story`; about 1,200 for each data skill |
| References a typical run reads | up to 52.9 KB for `story` | about 40 KB in chronicle; about 15 KB in briefing or blueprint |
| MCP servers in the main conversation | 0 | 0 |
| Source recipes loaded | `sources.md` on every story run | one per queried system, inside the gatherer |

### 4.11 Phases
Each phase gets a spec under `specs/` before code.

| Phase | Change | Release |
| --- | --- | --- |
| 0 | Install a plugin with a linked folder on claude.ai, Cowork and a Windows checkout; run one database through a user-level gatherer with inline `mcpServers`; check that the Google Drive and Microsoft 365 connectors can create a file | none |
| 1 | Carve the engine inside chronicle with no behavior change: registries, per-block assets, import test, vocabulary lint; move it to `packages/chronicle-engine` and link it | chronicle 0.5.0 |
| 2 | sources: detection, the source picker, MCP-lane recipes for all nine systems, `connect`; chronicle's researcher | sources 0.1.0, chronicle 0.6.0 |
| 3 | briefing: horizontal `deck`, `dashboard`, brand kit flags, `--to slides` and `--to dashboard`; keystone deck and dashboard | briefing 0.1.0 |
| 4 | blueprint: the TAD moves from chronicle; part details, pins and the step player; `prototype`; sequence and ERD kinds | blueprint 0.1.0, chronicle 0.7.0 |
| 5 | Script-lane collectors in the order users pick them; `refresh`; `--to google` and `--to microsoft`; impact-review links `packages/sources` and the engine's charts | sources 0.2.0, briefing 0.2.0, impact-review's next minor |
| 6 | Creative additions: rigs, panorama, tour, rooms, game scoring, plate notes, widget library | chronicle 0.8.0 |

## 5. Alternatives considered
- **A `mode` field in one skill.** Rejected: one `SKILL.md` would teach both workflows, so every run pays for both.
- **Two skill families in one plugin.** Rejected in answer 1. It needs no link, but every user pays for every description and all branches share one version.
- **Two plugins with copied engines and no sync.** Rejected: 6,400 lines would drift, and AGENTS.md rule 1 forbids copied blocks.
- **The engine as an MCP server.** Rejected for now (4.4): it costs context in every enabled session and gains nothing a CLI lacks in Claude Code. Kept as an opt-in plugin for shell-less hosts or MCP Apps.
- **The gatherer inside briefing.** Rejected: blueprint would depend on briefing and load its skills in every session.
- **One gatherer for every plugin (option C in 4.6).** Rejected: creative sessions would load the data plugin.
- **MCP servers bundled in a `plugin.json`.** Rejected: they start in every session where the plugin is enabled, with their instructions and tool names. Plugin agents ignore `mcpServers`, so a plugin cannot confine a server to its gatherer.
- **Existing skills for dashboards and decks** (`data:build-dashboard`, `anthropic-skills:pptx`). Rejected as the main path: neither reads chronicle's facts file, derive table or brand kit, so numbers lose their sources.

## 6. Risks and objections
- **Links may fail** on claude.ai, Cowork or Windows checkouts with `core.symlinks=false`. Phase 0 tests all three; the versioned package is the fallback.
- **Mis-routing** among four plugins. Trigger evals gate each release, and each description names the other plugins' requests.
- **More installs.** Installing briefing or blueprint installs sources through its dependency. chronicle works alone.
- **Every plugin on in one project** pays about 1,150 tokens of listings. The README shows `enabledPlugins` per project.
- **Creative pages with company data** need sources enabled. `story` says so when the gatherer is missing.
- **Database access** carries the most risk. The SQL guard, read-only sessions, timeouts and row caps run in code. Recipes ask for aggregates.
- **External deck targets** send company data to Google or Microsoft. They stay off by default, and each upload needs the user's confirmation under amendment 1.
- **Engine changes need every plugin green.** The 103 chronicle tests run in one command today; the split adds each plugin's suite to the same command.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only.
New: `packages/chronicle-engine/`, `packages/sources/`, `plugins/briefing/`, `plugins/blueprint/`, `plugins/sources/`.
Changed: `plugins/chronicle/`, `plugins/impact-review/` (phase 5), `.claude-plugin/marketplace.json`, `pyproject.toml` test and source paths, `CODEMAP.md`, `ARCHITECTURE.md`, and the `PROJECT.md` glossary (engine, branch, layout, brand kit, collector, recipe, queries file, researcher).

**Constitution check:**
- Principle 1 (scripts compute, Claude writes): improves. The script lane aggregates in code and SQL, so no model reads raw data. The MCP lane and the researcher keep RFC-0002's open question 3: raw text stays inside a subagent whose only outputs are a facts file and a digest.
- Principle 2 (every number has a source): extended. `queries.json` records the query behind each number, and the researcher records a locator for each fact.
- Principle 3 (local and private): **amended.** The guardrail "Never send collected data to a third-party service, including an MCP server, from plugin code" forbade `--to google` and `--to microsoft`, and publishing to claude.ai had the same tension (RFC-0002 open question 4). Answer 14 approved amendment 1, now in `CONSTITUTION.md` 1.1.0: "A publish to a destination the user names, such as a claude.ai Artifact, Google Drive or Microsoft 365, is allowed after the user confirms that publish."
- Principle 4 (read-only against sources): enforced in code by the SQL guard and the HTTPS allowlist. An upload to Google or Microsoft writes to a destination, never to a source being read.
- Principle 5 (one plugin, one job): improves. chronicle paints stories, briefing presents numbers, blueprint draws systems and sources reads data. The engine is a shared library with no manifest or skills.
- Guardrail on runtime dependencies: none added. Collectors use the standard library and the user's own `psql` and SQLcl. A PPTX writer would need its own approval.

## 8. Cross-repo contract
N/A, internal. Between the plugins the contract is files (`facts.json`, `queries.json`, `digest.md`, `material.md`, animation SVGs) and agent names (`sources:gatherer`, `chronicle:researcher`).

## 9. Out of scope
- Writing to any source system.
- Scheduled refresh; a later RFC could use scheduled tasks.
- A PPTX writer inside briefing; `--to slides` covers PPTX until a separate dependency decision.
- Renaming speedup to perf-optimizer, which RFC-0008 covers because it touches files in adopters' repositories (`perf/speedup.json`) and the data folder `~/speedup-runs/`.
- Bundling the three uploaded pages as examples. They stay outside the repo, and the evals use briefs that describe them.

## 10. Open questions
None. Section 3 records the answers to all sixteen questions.
Next: the owner approves with `/groundwork-specflow:approve`, then phase 0 gets the first spec under `specs/`.
