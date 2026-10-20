# chronicle

Illustrated, interactive story pages made for their subject: status reports, launches,
reviews, onboarding handbooks, training and guides. And standalone animations in the same
style, including animated technical architecture diagrams, that paste into web pages,
docs, READMEs, chat and slides.

Give Claude a brief ("the Q4 portfolio review of our order-platform migration", "a
first-week handbook for new store staff", "a guide to this podcast episode") and point it
at your data: connected GitHub, Jira, Confluence or Datadog, files, transcripts or pasted
notes. chronicle returns one long-form page in the manner of a newspaper graphics feature,
designed for that subject:

- **An identity from the subject's world.** A theme sets the palette, the type and a
  sticky progress bar shaped like something the subject uses: a parcel riding a conveyor,
  a tape measure, flags on a course, an interview clock, numbered steps, or a route the
  page draws itself (a trail, a coastline) walked by an icon it draws too. Chapter numbers
  become shipping labels, price tags, aisle signs or stamps; the hero numbers can print as
  a till receipt. The paper can be ruled, gridded or dotted, paintings can hang on a mat or
  be taped in, and every control speaks the subject's words ("Hole 3 of 9", "Field notes").
  Code derives dark mode and checks every text color for contrast.
- **No two pages alike.** Each theme starts from a written concept taken from the user's
  brand and files, the words of the request, or the material. `chronicle check` warns when
  a theme keeps chronicle's defaults or shares three features with an example or another
  run.
- **Illustrations drawn for the page.** Claude draws each picture as SVG (the packing
  table, the old system as a padlocked cabinet, the jammed conveyor) and a small OpenCV
  program paints it in ink and watercolor: loose washes with wet edges, granulation and
  shading, pen lines that overshoot their corners, paper texture. Labels on paintings stay
  live text and can hold facts; hotspots, steam, a turning beacon and a bobbing van move.
- **Editorial charts.** Line, stacked, bar, burnup with forecast fan, calendar heatmap,
  small multiples and slope charts, each with hover readouts and a table view.
- **Interactive figures.** Flows that compare a process then and now, tile maps that play
  through time, diagrams that step through a mechanism, quizzes and checklists for
  teaching, scrollytelling, an incident stepper, flip cards, a risk matrix, a roadmap, a
  team map, models with sliders, and custom widgets when nothing else fits.
- **A source behind every number.** Prose and painting labels hold tokens such as
  `{{plan.done_pct}}`; the page fills them from a facts file and shows each number's
  source on hover. Computed numbers come from code in a `derive` table, never the model.
- **Light and dark themes**, phone layouts (wide paintings pan as you scroll), keyboard
  access and reduced motion.

Three worked examples ship with the plugin, all with invented data:

- `examples/keystone/`: a status page for Fernhill Outfitters' order-platform migration,
  told through parcels, packing slips and a warehouse. A parcel rides a conveyor in the top
  bar, the hero numbers print as a till receipt, and a tile map plays the payments rollout
  state by state.
- `examples/onboarding/`: a first-week handbook for Saltmarsh Coffee Roasters. Chapters are
  marked as coffee lots; a flow follows a bean from green seed to cup, a tile map shows the
  origins, a widget lets new baristas dial in a shot, and a checklist and quiz close the week.
- `examples/quarterly/`: a short support-desk review for Lantern Bay, told as a lighthouse
  keeper's log: a lighthouse walks a coastline in the top bar, the paper is ruled, the
  numbers print on a ticket stub and chapters are stamped as watches.

## Animations

`/chronicle:animation` makes one animation that plays outside a story page. Three kinds
share one timeline, stage and theme:

- **`tad`**: a technical architecture diagram written as data: components with icons and
  their technology, groups (a VPC, a cluster, a trust boundary, vendors), sync and async
  links, and flows. Code places the parts in tiers, routes every line around the boxes,
  and plays the steps: parts appear and lines draw themselves on, packets run along a
  flow, the view focuses, and parts turn new, failing, down or planned.
- **`diagram`**: an SVG drawing in the story diagram format, played by id: parts appear,
  lines draw, packets run, the rest dims. A story page's diagram plays as it is.
- **`scene`**: a watercolor painting from a story drawing that washes from sketch into
  color, keeps its moving layers, and adds numbered callouts step by step.

Every animation is one SVG with no script: CSS keyframes on one clock, the theme scoped
to it, captions and a step strip, alt text with every step, and a still that shows the
whole picture under reduced motion. `animate build` also writes an HTML figure with a
pause button, and, with a local Chromium or Chrome, a poster PNG, a contact sheet of the
steps, a GIF from its own encoder, and an MP4 through ffmpeg (WebM without it).

```bash
scripts/chronicle animate new chronicle-runs/checkout --kind tad --title "Checkout"
scripts/chronicle animate check examples/animation-tad/animation.json
scripts/chronicle animate build examples/animation-tad/animation.json --formats svg,html,png,gif,mp4
```

| Example | Shows |
| --- | --- |
| `examples/animation-tad/` | an order's path through a checkout system: 10 components in 4 groups, 3 flows, a card processor going down and a planned fraud check |
| `examples/animation-diagram/` | a pull request's path to production, drawn as SVG, with a retry loop and a canary |
| `examples/animation-scene/` | the Keystone story's jammed conveyor, animated from the story's own drawing and facts |

## Install

```text
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install chronicle@10x-agent-marketplace
```

Requirements: [uv](https://docs.astral.sh/uv/) (recommended), which fetches NumPy and
OpenCV for painting on first use without touching your Python environment. Without uv,
Python 3.11+ with `numpy` and `opencv-python-headless` installed. Checking a story and
rendering a page without new paintings need only the Python standard library, as do an
animation's SVG and HTML. PNG, GIF and video exports need a Chromium or Chrome; MP4
needs `ffmpeg` on PATH.

## Use

In Claude Code: `/chronicle:story` with a brief, or ask for "an illustrated status page
for ...". For an animation: `/chronicle:animation`, or ask to "animate our checkout
architecture for the onboarding deck". The skill settles the brief, has the `chronicle-gatherer` subagent collect facts,
designs the page's identity, draws the illustrations, writes the story, builds it and
publishes it as a private Artifact.

From a shell:

```bash
scripts/chronicle new chronicle-runs/q4 --title "Q4 review"  # start a run folder
scripts/chronicle check examples/keystone/story.json     # validate story, theme, drawings
scripts/chronicle build examples/keystone/story.json     # derive, paint, render into build/
scripts/chronicle shoot examples/keystone/story.json     # desktop and phone screenshots
scripts/chronicle motifs                                 # landscape presets and motifs
```

`shoot` uses a Chromium or Chrome already installed (`--browser PATH` names one).

`build` writes:

| File | Use |
| --- | --- |
| `build/artifact.html` | the page to publish as an Artifact (no `<html>` wrapper) |
| `build/index.html` | the same page as a full document, to open locally |
| `build/art/*.webp` | paintings and their moving layers |
| `build/publish-files.json` | the `files` map for the Artifact tool |
| `build/single.html` | with `--inline`: one file with images embedded |
| `build/shots/*.png` | from `shoot`: the page at 1280 and 390 pixels wide |

## Files

| Path | Holds |
| --- | --- |
| `skills/story/` | the skill and its references: identity, illustration, story format, facts, sources, outlines, widgets, voice |
| `skills/animation/` | the animation skill and its references: the animation file, TADs, diagrams and scenes, export formats |
| `agents/chronicle-gatherer.md` | subagent that gathers facts from connected tools |
| `scripts/chronicle` | launcher used by the skill through `${CLAUDE_PLUGIN_ROOT}` |
| `src/chronicle/core/story/` | facts, derive, story checks, themes, the diagram sanitizer and the HTML renderer (standard library) |
| `src/chronicle/core/watercolor/` | the painting engine, the SVG reader and ink-and-wash painter, landscape motifs and presets |
| `src/chronicle/core/motion/` | animations: step clock, CSS keyframe timeline, stage, the diagram and scene kinds, the HTML figure and the GIF encoder |
| `src/chronicle/core/motion/tad/` | TADs: spec reader, layout, line routing, icons and the drawing |
| `src/chronicle/assets/` | the page's stylesheets, runtime scripts and font list; `motion/` holds the animations' stylesheets |
| `src/chronicle/connectors/files/` | every file read and write |
| `src/chronicle/connectors/browser/` | screenshots and animation frames through a headless Chromium or Chrome |
| `src/chronicle/connectors/video/` | MP4 through ffmpeg, WebM through OpenCV |
| `src/chronicle/entrypoints/cli/` | the command line |
| `examples/keystone/` | status page example: story, facts, SVG drawings and a diagram, with invented data |
| `examples/onboarding/` | handbook example: story, facts, drawings and a custom widget, with invented data |
| `examples/quarterly/` | support-desk review with a drawn route and icon, with invented data |
| `examples/animation-*/` | a TAD, a drawn diagram and a painted scene animation |
| `tests/` | pytest suite |

## Privacy

- Gathered data stays in the run folder on your machine until you publish.
- The skill asks before publishing data from company systems. Artifacts are private to
  you by default and hosted on claude.ai.
- The page loads fonts from Google Fonts; everything else is inline or published with it.
  An animation's SVG does the same where it is shown inline or opened directly.
- Animation frames are captured by a browser on your machine, and video is encoded by the
  ffmpeg program on your machine. Both run as argument lists with no shell, on the built
  files only.
- Diagrams pass an allowlist sanitizer; widget scripts are checked for network, storage
  and markup calls before a build.
- Source tools are only read, never written.

## Manual test

1. `scripts/chronicle build examples/keystone/story.json --out /tmp/keystone`
2. Open `/tmp/keystone/index.html` in a browser.
3. Scroll: a parcel rides the conveyor in the top bar from chapter to chapter; each
   painting develops from pencil to color as it arrives.
4. Hover any dotted number: its source and note appear.
5. In chapter 03, switch the order path between Mar 2025 and Oct 2026, select a step, and
   press Play on the payments map.
6. In chapter 04, step through the jam diagram and the incident chart with Next.
7. In chapter 07, select the stops on the route map, then drag the forecast sliders.
8. Switch the theme with the round button; paintings move onto paper plates.
9. Narrow the window below 700 px: wide paintings pan sideways as you scroll.
10. Build `examples/onboarding/story.json` the same way. Move the grinder slider in chapter 03
    until the shot lands in the window, tick two checklist items in chapter 04 and reload
    (the ticks stay), then answer the quiz in chapter 05: it asks "Cup 1 of 5".
11. Build `examples/quarterly/story.json`. A lighthouse walks a dashed coastline in the
    top bar as you scroll; the paper is ruled; "Open the log" under the chart shows its
    numbers.
12. `scripts/chronicle shoot examples/quarterly/story.json --out /tmp/quarterly` writes
    `shots/desktop.png` and `shots/phone.png` with the painting in color.
13. `scripts/chronicle animate build examples/animation-tad/animation.json --out /tmp/tad
    --formats svg,html,png,gif,mp4`, then open `/tmp/tad/index.html`. The web app and
    gateway appear, the order service's lines draw on, a packet runs from the web app to
    the card processor, events run to the workers, the view dims around a card processor
    marked DOWN, and a planned fraud check appears. Hover the figure and press Pause.
14. Open `/tmp/tad/animation.gif`, `animation.mp4` and `poster.png`; the poster shows every
    part. Look at `steps.png`: one frame per step.
15. Build `examples/animation-scene/animation.json`: the painting washes from gray to color,
    the beacon turns, and three numbered spots come in with the focus.

## License

MIT, copyright 2026 Jacqueline Dean. See [LICENSE](LICENSE).

The plugin bundles no third-party code. Painting uses NumPy (BSD 3-clause) and
`opencv-python-headless` (Apache 2.0, with FFmpeg under LGPL 2.1), which uv downloads from
PyPI into its own cache. Those wheels carry their own license files, including OpenCV's
`LICENSE-3RD-PARTY.txt`.
