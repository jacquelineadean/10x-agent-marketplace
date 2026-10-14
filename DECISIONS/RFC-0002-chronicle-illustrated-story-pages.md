---
id: RFC-0002
title: chronicle plugin: illustrated, interactive story pages
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude Code session, 14 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0001]
author: Claude Code, for Jacqueline Dean
created: 2026-10-14
---

# RFC-0002 — chronicle plugin: illustrated, interactive story pages

## 1. Summary
Add a second plugin, **chronicle**, that turns a brief plus gathered facts into one
illustrated, interactive web page published as a private claude.ai Artifact.
A standard-library renderer builds the page from two files: `facts.json` (every number,
with its source) and `story.json` (chapters and blocks that cite facts by token).
A small OpenCV and NumPy program paints watercolor plates that show the real state of the
subject. The proof of concept, `examples/keystone/`, is a status page for an invented
platform migration.

The request asked to build first and iterate; this RFC records the decisions after the
fact so they can be approved, changed or rejected before merge. It conflicts with three
Constitution rules (section 7), which need an explicit decision.

## 2. The need
**User scenario:** Jacqueline Dean liked an illustrated, interactive companion page for a
podcast episode and wants the same treatment for work forums: a software project's status,
achievements, challenges, opportunities, history, roadmap and team, from what the user
provides and from connected MCP servers (GitHub, Atlassian, Datadog). Pages should be
beautiful, interactive, focused on the highlights, with watercolor illustrations and data
visualisation "in the manner of the New Yorker or the New York Times".
**Done means:** one skill in Claude Code produces a published Artifact from a brief; every
number on the page traces to a fact with a source; the Keystone example shows every block
type with mock data; the four quality gates pass.

## 3. Interview record
No interview was held; the session request was explicit and asked for autonomous work.
Answers below are taken from the request or assumed, and assumed ones are open decisions.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | What is built? | A reusable plugin that builds interactive, illustrated artifacts from provided content | From request |
| 2 | Example subject? | IT software project: status, achievements, challenges, opportunities, history, roadmap, team | From request |
| 3 | Data sources? | User-provided content and MCP servers such as GitHub, Jira, Confluence, Datadog | From request |
| 4 | Illustration technique? | Watercolor painted with OpenCV | From request |
| 5 | Proof of concept data? | Mock data for one project | From request |
| 6 | Plugin name? | chronicle | Assumed, open |
| 7 | Where does the page live? | Private claude.ai Artifact, published after the user confirms | Assumed, open |
| 8 | Runtime dependencies? | NumPy and OpenCV, for painting only | Assumed, needs approval (7) |

### Read-back
- **Confirmed by the request:** plugin in this marketplace; narrative, illustrated, interactive pages; MCP and pasted sources; OpenCV watercolor; mock proof of concept.
- **Tensions:** see section 7.
- **Open decisions:** name; Artifact as the delivery surface; the three Constitution items.

## 4. Proposal

### 4.1 What the user runs
- `/chronicle:story` with a brief, or a request such as "an illustrated status page for X".
- Shell: `scripts/chronicle check|build|motifs STORY` (the skill calls it through `${CLAUDE_PLUGIN_ROOT}`).

### 4.2 Plugin contents (`plugins/chronicle/`)
| Path | Role |
| --- | --- |
| `skills/story/SKILL.md` + `references/` | The workflow: brief, gather, write, build, publish; story format, facts, sources, outlines, scenes, voice |
| `agents/chronicle-gatherer.md` | Subagent that queries connected tools and writes `facts.json`; raw tool output never enters the main conversation |
| `scripts/chronicle` | Launcher: `uv run` with NumPy and OpenCV when uv exists, else `python3` |
| `src/chronicle/` | `core/story` (facts, derive, checks, renderer; standard library), `core/watercolor` (painting), `assets` (CSS and JS), `connectors/files`, `entrypoints/cli` |
| `examples/keystone/` | Worked example with invented data |

### 4.3 Pipeline
1. Brief with the user (at most four questions).
2. Gather into `facts.json`: records with value, unit, source, note; series as arrays.
3. Write `story.json`: chapters of blocks; numbers only as `{{path|format}}` tokens; data as `"@path"` references.
4. `chronicle build`: run the `derive` table, check the story, paint changed scenes (cached by scene and engine hash), render `artifact.html`, `index.html`, `art/*.webp`, `publish-files.json`.
5. Publish with the Artifact tool after the user confirms; republish to the same path to update.

### 4.4 Page
15 block types: prose, stats, lesson, quote, chart (line, area, stacked, bars, burnup, calendar, multiples, slope), scrolly, timeline, stepper, compare, matrix, roadmap, team, model (forecast, savings), table, plate.
All words are static HTML; a 1,350-line vanilla script draws charts and interactions from one JSON blob. No chart library. Text from sources is escaped in HTML and in the JSON blob.
Theme: light and dark tokens; categorical palette validated for colour-vision deficiency; paintings sit on paper plates in dark mode.

### 4.5 Facts and the derive table
Computed numbers (last, total, mean_last, growth_last, diff, ratio, share, pct_change, burnup_sprints, burnup_finish, weeks_between) are produced by code from gathered series. The burnup forecast uses the same rule as the page's chart, so the prose and the chart agree.
`chronicle check` errors on unknown tokens and warns on numbers typed into prose.

### 4.6 Painting engine
Image-space watercolor after Curtis et al. (1997) and Bousseau et al. (2006): washes as pigment density with edge darkening, flow noise, granulation into a paper height map, backruns, wet-in-wet edges and multiplicative glazing; pen and pencil lines; deckle and spot vignettes.
Nine presets (a bridge story, a road, a valley, a waterfront, a vignette) and a JSON motif language with 19 motifs and 8 brush primitives for new scenes. Moving layers (descend, drift, fall, cross) and named anchors let the page animate parts and pin hotspots.
A 1,800-pixel plate takes 2 to 4 seconds and 60 to 100 KB as WebP.

### 4.7 Token budget
The skill reads its references on demand (about 6,000 tokens). The gatherer's tool output stays in the subagent. A Keystone-sized story file is about 9,000 tokens to write. Build output is under 20 lines.

## 5. Alternatives considered
- **Claude writes each page's HTML by hand.** Rejected: inconsistent quality, numbers typed from memory, and several times the tokens per page.
- **Chart libraries from a CDN (D3, Vega-Lite).** Rejected for now: the hand-built charts are small, follow the dataviz palette rules and keep the page self-contained.
- **Image-generation models for illustrations.** Rejected: not available offline, not deterministic, and cannot paint exact state such as 3.75 arches.
- **Artifact Dashboard type.** Rejected for this use: built for metric grids, not for narrative chapters with paintings.
- **SVG illustrations only.** Rejected: flat vector art loses the paper and pigment texture that gives the pages their character.

## 6. Risks and objections
- **Runtime dependencies** on machines without uv or wheels for OpenCV. Mitigation: painting is optional (`--no-paint`); rendering is standard library.
- **Publishing company data.** Mitigation: the skill asks first; Artifacts are private by default.
- **Mock data mistaken for real.** Mitigation: byline and colophon state it; the skill requires this for invented data.
- **Painting quality varies for new scenes.** Mitigation: presets for common metaphors; the skill tells Claude to look at each painting and adjust.
- **Fonts load from Google Fonts at view time.** Fallback stacks keep the page readable offline.
- **The JS runtime has no unit tests.** Python tests cover the HTML and data; the page was checked in Chromium at 1280 and 390 pixels in both themes. A browser test suite is future work.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. Adds `.claude-plugin/marketplace.json` (impact-review joins it once it has a manifest).
**Constitution check:**
- Principle 1 (scripts compute, Claude writes): the renderer, derive table and painter compute; Claude writes the story. **Conflict:** the gatherer subagent reads raw MCP responses. Proposed amendment: raw source data may be read inside a subagent whose only output is a facts file.
- Principle 2 (every number has a source): met by tokens, `derive` and the check command.
- Principle 3 (local and private): the plugin's own code makes no network calls. **Conflict:** publishing sends the page to claude.ai. Proposed amendment: allowed after the user confirms, never automatic.
- Principle 4 (read-only): the gatherer is instructed to read only.
- Principle 5 (one plugin, one job): own folder, version and README.
- Guardrail "no runtime dependency without an approved RFC": **this RFC requests** `numpy>=2.0` and `opencv-python-headless>=4.10`, for painting only, fetched by uv into its cache.
**Cost / performance / security notes:** text from sources is escaped; the JSON blob escapes `<`, `>` and `&`; links allow only http(s) and page anchors.

## 8. Cross-repo contract
N/A, internal.

## 9. Out of scope
- A hosted service or scheduled refresh; PDF or slide export.
- Turning photographs into watercolors (a natural next step for team pages).
- Collector code per source (the gatherer uses MCP tools; RFC-0001's collector pattern could follow for heavy sources).

## 10. Open questions
1. Approve the name `chronicle`?
2. Approve the two runtime dependencies for painting?
3. Amend principle 1 for the gatherer subagent, or require collector scripts per source first?
4. Amend principle 3 for user-confirmed Artifact publishing?
