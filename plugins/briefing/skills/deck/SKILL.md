---
name: deck
description: Build a slide deck from facts as an interactive HTML Artifact of 16:9 slides that a presenter clicks through, in place of PowerPoint, with builds, speaker notes, KPI tiles, charts and stepped animations; or as claude.ai Slides, PDF or PNG. Use for quarterly and business reviews, steering committees, decision decks, launch readouts and executive briefings. For illustrated stories use chronicle; for system diagrams use blueprint.
---

# Decks from facts

A deck is fixed 16:9 slides on a horizontal track. Every number on a slide is a fact
token with its source and query on hover. Code computes every number, its status and its
format; you write the slides.

| Step | Who | Output (run folder) |
| --- | --- | --- |
| 1. Brief | you, with the user; `briefing new --layout deck` | `story.json` |
| 2. Facts | `sources:gatherer`, or the user's pasted numbers | `facts.json`, `queries.json`, `digest.md` |
| 3. Write | you | `story.json` |
| 4. Build and look | `briefing build`, then `briefing slides --png` | `build/artifact.html`, `build/slides/*.png` |
| 5. Publish | you, after the user confirms | an Artifact, Slides, a PDF or PNGs |

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" new briefing-runs/<slug> --layout deck --title "Title"
```
Add `--brand repo`, `--brand config` or `--brand PATH` to copy a brand kit into the folder.
Read `${CLAUDE_PLUGIN_ROOT}/references/brand.md` when the user has a house style.

## 1. Brief
Ask only what the request leaves open, in one AskUserQuestion: the audience and forum,
the decision or point the deck must land, the window, the systems to read, and the format
(Artifact, Slides, PDF or PNGs).

## 2. Facts
Call `sources:gatherer` with `Mode: gather`, the run folder, the systems, the window and
the brief. When the request names no system, run
`"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" sources detect --picker --connectors <names>`, where
`<names>` lists the MCP server names in your tool list, and pass its output as
AskUserQuestion's `questions`. Read `digest.md`, never `facts.json` or tool output. Put
every computed number in the facts file's `derive` table
(`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/facts.md`).

## 3. Write
Read `references/deck-format.md` and `${CLAUDE_PLUGIN_ROOT}/references/voice.md`.
- The first slide is the cover from `meta`; the last lists the sources. Each chapter is one
  slide between them.
- Lead with the decision. Give each KPI its target and period, and each risk an owner.
- One idea per slide, at most 60 words and 4 blocks. Use `build` to reveal a point on click.
- Put what the presenter says in `notes`.

## 4. Build and look
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" check briefing-runs/<slug>/story.json
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" build briefing-runs/<slug>/story.json
"${CLAUDE_PLUGIN_ROOT}/scripts/briefing" slides briefing-runs/<slug>/story.json --png
```
Fix every error and each warning you can. Look at every slide image with the Read tool:
text that overflows, a chart too small to read, or an empty slide means rewriting it.

## 5. Publish
Confirm the destination with the user first.
- **Artifact** (default): publish `build/artifact.html` with the Artifact tool; map the
  files in `build/publish-files.json`.
- **Slides** (`--to slides`): run `briefing export <story> --to slides`, then start from
  claude.ai's Slides type (Artifact quickstart, intent `slides`) and fill it from
  `build/slides.json`, one slide per entry, using its images. It downloads as PPTX or PDF.
- **PDF or PNGs**: `briefing slides <story> --pdf` writes `build/deck.pdf`.

Arrow keys, swipes and the arrow buttons step through the deck; `O` shows the overview,
`Notes` shows speaker notes.
