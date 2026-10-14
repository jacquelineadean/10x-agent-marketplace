# chronicle

Illustrated, interactive story pages for status reports, reviews and recaps.

Give Claude a brief ("the Q4 portfolio review of our order-platform migration") and point
it at your data: connected GitHub, Jira, Confluence or Datadog, files, or pasted notes.
chronicle returns one long-form page in the manner of a newspaper graphics feature:

- **Watercolor plates painted in code.** A small OpenCV program lays transparent washes
  with wet edges, granulation and backruns, draws pen lines and leaves paper texture. The
  paintings show the real state: three of five arches built means three arches painted.
  Parts of a painting move as you read: a keystone lowers into its arch, rain falls.
- **Editorial charts.** Line, stacked, bar, burnup with forecast fan, calendar heatmap,
  small multiples and slope charts, each with hover readouts and a table view.
- **Interactive figures.** Scrollytelling, an incident stepper, flip cards, a risk matrix,
  a roadmap, a team map, and models with sliders for forecasts and costs.
- **A source behind every number.** Prose holds tokens such as `{{plan.done_pct}}`; the
  page fills them from a facts file and shows each number's source on hover. Computed
  numbers come from code in a `derive` table, never from the model.
- **Light and dark themes**, phone layouts, keyboard access and reduced motion.

The worked example, `examples/keystone/`, is a status page for an invented order-platform
migration at an invented retailer.

## Install

```text
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install chronicle@10x-agent-marketplace
```

Requirements: [uv](https://docs.astral.sh/uv/) (recommended), which fetches NumPy and
OpenCV for painting on first use without touching your Python environment. Without uv,
Python 3.11+ with `numpy` and `opencv-python-headless` installed. Rendering a page without
new paintings needs only the Python standard library.

## Use

In Claude Code: `/chronicle:story` with a brief, or ask for "an illustrated status page
for ...". The skill settles the brief, has the `chronicle-gatherer` subagent collect facts,
writes the story, builds it and publishes it as a private Artifact.

From a shell:

```bash
scripts/chronicle check examples/keystone/story.json     # validate story and facts
scripts/chronicle build examples/keystone/story.json     # derive, paint, render into build/
scripts/chronicle motifs                                 # presets and motifs for scenes
```

`build` writes:

| File | Use |
| --- | --- |
| `build/artifact.html` | the page to publish as an Artifact (no `<html>` wrapper) |
| `build/index.html` | the same page as a full document, to open locally |
| `build/art/*.webp` | paintings and their moving layers |
| `build/publish-files.json` | the `files` map for the Artifact tool |
| `build/single.html` | with `--inline`: one file with images embedded |

## Files

| Path | Holds |
| --- | --- |
| `skills/story/` | the skill and its references: story format, facts, sources, outlines, scenes, voice |
| `agents/chronicle-gatherer.md` | subagent that gathers facts from connected tools |
| `scripts/chronicle` | launcher used by the skill through `${CLAUDE_PLUGIN_ROOT}` |
| `src/chronicle/core/story/` | facts, derive, story checks and the HTML renderer (standard library) |
| `src/chronicle/core/watercolor/` | the painting engine, motifs, presets and scene language |
| `src/chronicle/assets/` | the page's stylesheet and runtime script |
| `src/chronicle/connectors/files/` | every file read and write |
| `src/chronicle/entrypoints/cli/` | the command line |
| `examples/keystone/` | example `story.json` and `facts.json` with invented data |
| `tests/` | pytest suite |

## Privacy

- Gathered data stays in the run folder on your machine until you publish.
- The skill asks before publishing data from company systems. Artifacts are private to
  you by default and hosted on claude.ai.
- The page loads fonts from Google Fonts; everything else is inline or published with it.
- Source tools are only read, never written.

## Manual test

1. `scripts/chronicle build examples/keystone/story.json --out /tmp/keystone`
2. Open `/tmp/keystone/index.html` in a browser.
3. Scroll: the arches in the top bar fill chapter by chapter; the hero keystone lowers
   into its arch; the share chart in chapter III follows the step cards.
4. Hover any dotted number: its source and note appear.
5. In chapter IV, step through the incident with Next; in chapter VII drag the sliders and
   watch the projected finish date and the sentence below change.
6. Switch the theme with the round button; paintings move onto paper plates.
