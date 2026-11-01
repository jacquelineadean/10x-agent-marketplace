---
name: architecture
description: Build interactive system and data design visuals, still or animated: technical architecture diagrams of services, zones and request or event flows laid out in code, sequence diagrams and ERDs, each played step by step, on a page where parts open their details, pins mark decisions and a player steps through the flows. Exports SVG, HTML, PNG, GIF and MP4. Use for "animate our architecture", system design reviews, request and data flows, schema walkthroughs and onboarding to a codebase. For illustrated stories use chronicle; for KPI dashboards and decks use briefing.
---

# Architecture visuals

Each figure is an `animation.json`: data that code lays out, routes, times and draws into
one SVG whose motion is CSS keyframes on one clock. An architecture page wraps a built SVG
in the `architecture` block, which adds part details, pins and a step player.

| Kind | Claude writes | Reference |
| --- | --- | --- |
| `tad` | components, groups, links and flows; code places and routes them | `references/tad.md` |
| `sequence` | participants and messages in order | `references/sequence.md` |
| `erd` | tables, key columns and relations, or `blueprint schema` from an export | `references/erd.md` |
| `diagram` | an SVG drawing with ids, when the figure is not boxes and links | the engine's `blocks.md` |

## 1. Brief
Ask only what the request leaves open, in one AskUserQuestion: where it goes (a page, a
deck, docs, a README, a slide), the point the steps build toward, and the sources (design
docs, repositories, schemas, runbooks). When facts come from company systems, call
`sources:gatherer`; run `"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" sources detect --picker
--connectors <names>` for the picker when the request names no system.

## 2. Write the figure
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" animate new blueprint-runs/<slug> --kind tad --title "Title"
```
Read `${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/animation-format.md` for the
shared keys, steps and timing, then the kind's reference. 6 to 14 parts read well in 16:9;
split a larger system into two figures. Write 3 to 6 steps, one idea each, and let code
time them. Numbers in labels and captions are fact tokens.

For an ERD from a database, read its catalog live with
`"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" schema --connection postgres --out erd.json`
(Postgres or Oracle; see `references/erd.md`), or export it as CSV and pass the file. For a
Databricks table's lineage, `blueprint lineage <catalog.schema.table> --out <run>/animation.json`
writes a TAD of the tables it is built from and the tables built from it.

## 3. Build and look
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" animate check blueprint-runs/<slug>/animation.json
"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" animate build blueprint-runs/<slug>/animation.json --formats svg,html,png,gif
```
Read `build/steps.png` with the Read tool. A warning that the TAD is shrunk below 62
percent means the frame is too small: use `"size": "wide"`, the `down` direction, or fewer
parts.

## 4. The interactive page (optional)
Read `references/architecture-format.md`. Start a page with
`"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" new blueprint-runs/<slug>-page`, add an
`architecture` block naming the built SVG, describe the parts a reader will ask about in
`parts`, and mark decisions and open questions with `pins`. Then `check`, `build`, and
`shoot`; `check` refuses a part or pin the SVG does not hold.

## 5. Deliver
Give the formats that fit where it goes
(`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/formats.md`). Publish
`build/index.html` or the page's `build/artifact.html` with the Artifact tool after the
user confirms. A briefing deck plays the SVG one step per click through its `animation`
block.
