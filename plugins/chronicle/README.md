# chronicle

Illustrated, interactive story pages made for their subject: status reports, launches,
reviews, onboarding handbooks, training and guides. And standalone animations in the same
style, including animated technical architecture diagrams, that paste into web pages,
docs, READMEs, chat and slides.

Give Claude a brief ("the Q4 portfolio review of our order-platform migration", "a
first-week handbook for new store staff", "a guide to this podcast episode") and point it
at your material: files, transcripts, links or pasted notes, and company systems through
the sources plugin. chronicle returns one long-form page in the manner of a newspaper graphics feature,
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
  team map, models with sliders, and custom widgets when nothing else fits. A widget
  library keeps drills written once (order, match, sort, flash cards) for the next page.
- **Places to explore.** A panorama to drag along, with animals drawn in parts that walk,
  swim, crawl, glide and leap, places named along the top, a tide slider and a field
  journal that remembers every animal found; rooms walked through painted doorways; and a
  map tour whose stops open those scenes while a route in the top bar follows the reader.
- **Games and notes.** Quizzes played as golf holes, with a flag per hole in the top bar
  and a closing scorecard; red-pen notes that write themselves over a painting.
- **A source behind every number.** Prose and painting labels hold tokens such as
  `{{plan.done_pct}}`; the page fills them from a facts file and shows each number's
  source on hover. Computed numbers come from code in a `derive` table, never the model.
- **Light and dark themes**, phone layouts (wide paintings pan as you scroll), keyboard
  access and reduced motion.

Four worked examples ship with the plugin, all with invented data:

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
- `examples/field-guide/`: a field guide to Marrow Key, an invented barrier island. A map
  tour opens the dock, the keeper's house (walked room to room), the salt marsh and the
  live oaks; the marsh is a panorama with a heron, hogs, fiddler crabs, a gull and a
  dolphin, a tide and a journal; pen notes mark the plates; a quiz plays as two holes.

## Animations

`/chronicle:animation` makes one animation that plays outside a story page. Three kinds
share one timeline, stage and theme (technical architecture diagrams moved to blueprint):

- **`diagram`**: an SVG drawing in the story diagram format, played by id: parts appear,
  lines draw, packets run, the rest dims. A story page's diagram plays as it is.
- **`scene`**: a watercolor painting from a story drawing that washes from sketch into
  color, keeps its moving layers and rigs, and adds numbered callouts step by step.
- **`rig`**: an animal or machine drawn in parts, playing its gait on the loop: a trot, a
  grazing head, a waving claw, beating wings.

Every animation is one SVG with no script: CSS keyframes on one clock, the theme scoped
to it, captions and a step strip, alt text with every step, and a still that shows the
whole picture under reduced motion. `animate build` also writes an HTML figure with a
pause button, and, with a local Chromium or Chrome, a poster PNG, a contact sheet of the
steps, a GIF from its own encoder, and an MP4 through ffmpeg (WebM without it).

```bash
scripts/chronicle animate new chronicle-runs/release --kind diagram --title "Release"
scripts/chronicle animate check examples/animation-diagram/animation.json
scripts/chronicle animate build examples/animation-diagram/animation.json --formats svg,html,png,gif,mp4
```

| Example | Shows |
| --- | --- |
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
architecture for the onboarding deck". The skill settles the brief, has the `researcher` subagent digest the material (and,
with the sources plugin, `sources:gatherer` read company systems),
designs the page's identity, draws the illustrations, writes the story, builds it and
publishes it as a private Artifact.

From a shell:

```bash
scripts/chronicle new chronicle-runs/q4 --title "Q4 review"  # start a run folder
scripts/chronicle check examples/keystone/story.json     # validate story, theme, drawings
scripts/chronicle build examples/keystone/story.json     # derive, paint, render into build/
scripts/chronicle shoot examples/keystone/story.json     # desktop and phone screenshots
scripts/chronicle motifs                                 # landscape presets and motifs
scripts/chronicle widgets list                           # the widget library
scripts/chronicle widgets add sort-drill chronicle-runs/q4      # copy a drill into a run
scripts/chronicle widgets save chronicle-runs/q4 shot-timer     # keep a run's widget
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
| `skills/animation/` | the animation skill and its reference on diagrams and scenes; the animation file and export formats are engine references |
| `agents/researcher.md` | subagent that reads the material (files, transcripts, links, web, document connectors) and writes `research/facts.json` with a locator on every fact and `research/material.md` |
| `scripts/chronicle` | launcher used by the skill through `${CLAUDE_PLUGIN_ROOT}` |
| `src/chronicle_engine` | a link to `packages/chronicle-engine/src/chronicle_engine`, the shared engine: facts, derive, story checks and renderer, theme tokens, the animation clock and stage, the diagram kind, file, browser and video connectors, and the command line. Claude Code copies the linked files at install |
| `src/chronicle/pack.py` | chronicle's registrations with the engine: the painter as art provider, the `plate`, `panorama`, `rooms`, `tour` and `scorecard` blocks and quizzes as holes, the page chrome, the scene and rig kinds, the sameness review (`distinct` policy) and the `motifs`, `research` and `widgets` commands |
| `src/chronicle/core/story/` | plates, pen notes and rigs on the page (`plates.py`), the panorama, rooms and tour blocks, game scoring (`game.py`), the widget library's format (`library.py`), the progress devices, chapter marks, stat slips and frames a theme picks (`chrome.py`), and the sameness review (`review.py`) |
| `src/chronicle/core/watercolor/` | the painting engine, the SVG reader (layers, anchors, rigs) and ink-and-wash painter, landscape motifs and presets |
| `src/chronicle/core/motion/` | the scene and rig kinds |
| `src/chronicle/assets/` | chronicle's own page and animation parts: plates, notes, rigs, panorama, rooms, tour and game stylesheets and runtimes, the identity stylesheets and progress devices, the scene stylesheet |
| `src/chronicle/entrypoints/cli/` | painting shared by `build`, `paint` and `animate` (`art.py`), and the `motifs`, `research` and `widgets` commands |
| `widgets/` | the bundled widget library: order, match, sort and flash drills |
| `examples/keystone/` | status page example: story, facts, SVG drawings and a diagram, with invented data |
| `examples/onboarding/` | handbook example: story, facts, drawings and a custom widget, with invented data |
| `examples/quarterly/` | support-desk review with a drawn route and icon, with invented data |
| `examples/field-guide/` | island field guide: a tour, rooms, a panorama with rigged animals, notes and holes, with invented data |
| `examples/animation-*/` | a drawn diagram and a painted scene animation |
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
13. `scripts/chronicle animate build examples/animation-diagram/animation.json --out
    /tmp/diagram --formats svg,html,png,gif,mp4`, then open `/tmp/diagram/index.html`. The
    pull request, CI and review boxes appear, the retry loop draws, and a packet runs to
    production through the canary. Hover the figure and press Pause.
14. Open `/tmp/diagram/animation.gif`, `animation.mp4` and `poster.png`; the poster shows
    every part. Look at `steps.png`: one frame per step.
15. Build `examples/animation-scene/animation.json`: the painting washes from gray to color,
    the beacon turns, and three numbered spots come in with the focus.
16. Build `examples/field-guide/story.json` and open it. Pick stop 2 on the map: the map
    zooms into the keeper's house; walk in through the door, then press "Next stop" for
    the marsh. The route in the top bar marks the stops visited.
17. In the marsh chapter, press "Mudflat", then move the tide to High: the crabs go and
    the dolphin leaps off the beach. Pick the heron; the journal counts 1 of 5. Reload:
    the journal and the tour's visits stay.
18. Play the two holes in the last chapter: each flag in the top bar takes the hole's
    color and the scorecard totals the round. The hog under the oaks roots with its head
    down and its tail going; the pen notes write themselves over the plates.

## License

MIT, copyright 2026 Jacqueline Dean. See [LICENSE](LICENSE).

The plugin bundles no third-party code. Painting uses NumPy (BSD 3-clause) and
`opencv-python-headless` (Apache 2.0, with FFmpeg under LGPL 2.1), which uv downloads from
PyPI into its own cache. Those wheels carry their own license files, including OpenCV's
`LICENSE-3RD-PARTY.txt`.
