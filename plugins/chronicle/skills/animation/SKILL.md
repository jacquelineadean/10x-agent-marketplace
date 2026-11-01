---
name: animation
description: Make a standalone animation, in the chronicle story style, that plays anywhere: an animated technical architecture diagram (TAD) of services, zones and request or event flows; an animated diagram drawn as SVG; or a painted watercolor scene with callouts. Exports one self-contained SVG, an HTML embed, a poster PNG, a GIF and an MP4 for web pages, docs sites, READMEs, Confluence, Notion, Slack, email and slides. Use for "animate our architecture", "show how a request moves through the system", system design walkthroughs, incident and data-flow explainers, onboarding visuals, or any figure or story moment that should move outside a story page.
---

# chronicle animation: standalone animations that paste into anything

An animation is one `animation.json` in a run folder. Claude writes what the figure shows
and the steps it plays; code lays it out, times it, draws it and exports it. The output
is a single SVG whose motion is CSS keyframes on one clock, so the same file plays in a
browser, inside an HTML page, as an `<img>`, and frame by frame for GIF and video.

Three kinds share the timeline, the stage (title, captions, step bar) and the theme:

| Kind | Claude writes | Use for |
| --- | --- | --- |
| `tad` | components, groups, links and flows as data; code places and routes them | architecture, request paths, event flows, failure and migration walkthroughs |
| `diagram` | an SVG drawing with ids, in the story diagram format | a mechanism, a pipeline, any drawn figure, a story page's diagram as it is |
| `scene` | a watercolor drawing (as for a story plate) and numbered spots | a story moment: an incident, a launch, a place |

Pick `tad` whenever the subject is software made of parts that talk to each other. Pick
`diagram` when the figure is not boxes and links, or the user already has the drawing.
Pick `scene` when a picture carries the point better than a chart.

## 1. Settle the brief

Ask only what the request leaves open (one AskUserQuestion, at most 3 questions):

- **Where it goes**: a web page, docs, a README, Confluence or Notion, Slack, email, a
  slide. This picks the formats (`${CLAUDE_PLUGIN_ROOT}/skills/animation/references/formats.md`) and the frame size.
- **The point**: the one thing the viewer should understand. Steps build toward it.
- **Sources**: the design doc, repo, diagrams, runbook or notes the parts come from.

Note brand colors and type. With mock data, say so in `meta.credit` ("Example data").

## 2. Start the run folder

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/chronicle" animate new chronicle-runs/<slug> --kind tad --title "Title"
```

It writes `animation.json` and `facts.json` (and `drawing.svg` for a diagram) and adds
the runs folder to `.gitignore` in a git working directory.

## 3. Write the figure

Read `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/animation-format.md` for the shared keys, the steps and timing. Then:

- **tad**: read `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/tad.md`. List the components from the sources, group them
  by trust boundary or deployment (VPC, cluster, vendors), add the links with their
  protocol as labels, and name the flows the viewer should watch. 6 to 14 nodes read
  well in 16:9; split a larger system into two animations.
- **diagram**: read `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/diagram-and-scene.md` and the diagram classes in the
  story skill's `${CLAUDE_PLUGIN_ROOT}/skills/story/references/story-format.md`. Give every part an `id`; give each path a
  packet runs along an `id` and draw it in the direction of travel.
- **scene**: read `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/diagram-and-scene.md` and the story skill's
  `${CLAUDE_PLUGIN_ROOT}/skills/story/references/illustration.md`. Put a `data-anchor` where each spot goes.

Numbers in captions, labels and drawings are fact tokens (`{{ci.median_minutes}}`), as
in a story. Write `theme.concept` first, then the palette and fonts, as in the story
skill's `${CLAUDE_PLUGIN_ROOT}/skills/story/references/identity.md`.

## 4. Write the steps

Each step is one beat with a caption of one sentence. 3 to 6 steps; the first shows the
entry point, the last lands the point. A step shows parts, runs flows, focuses, pulses
and sets states. Code times each step from its caption's reading time and what it plays.

## 5. Build and look

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/chronicle" animate check chronicle-runs/<slug>/animation.json
"${CLAUDE_PLUGIN_ROOT}/scripts/chronicle" animate build chronicle-runs/<slug>/animation.json --formats svg,html,png,gif
```

`check` validates ids, fact tokens, the drawing and the theme. `build` writes into
`build/`: `animation.svg`, `embed.html`, `index.html`, and with a local Chromium or
Chrome `steps.png` (the end of every step), `poster.png` (the still) and the GIF. Add
`mp4` for slides and chat (needs ffmpeg; WebM is written without it).

Read `build/steps.png` with the Read tool before sharing. Fix overlapping labels, parts
that appear in the wrong step and text that is too small, then build again. A warning
that the TAD is shrunk means the frame is too small for it: use `"size": "wide"`, the
`down` direction for tall frames, or fewer parts.

## 6. Deliver

- Give the files that fit where it goes (`${CLAUDE_PLUGIN_ROOT}/skills/animation/references/formats.md`), with one line each.
- To share a link, publish `build/index.html` with the Artifact tool (`icon: "chart"`,
  a one-sentence `description`). Ask once first when the figure holds company data.
- To change it, edit `animation.json`, rebuild and republish the same path.

## Files

- `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/animation-format.md`: the animation file, frames, timing, steps per kind.
- `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/tad.md`: the `tad` object: nodes, kinds, groups, edges, flows, states, layout.
- `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/diagram-and-scene.md`: drawn diagrams and painted scenes.
- `${CLAUDE_PLUGIN_ROOT}/skills/animation/references/formats.md`: each export and where to use it, with embed snippets.
- `${CLAUDE_PLUGIN_ROOT}/examples/animation-tad/`: an order's path through a checkout
  system, with a failure step and a planned component (invented data).
- `${CLAUDE_PLUGIN_ROOT}/examples/animation-diagram/`: a pull request's path to production.
- `${CLAUDE_PLUGIN_ROOT}/examples/animation-scene/`: the Keystone story's jammed conveyor,
  animated from the story's own drawing and facts.
