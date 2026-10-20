---
id: RFC-0005
title: chronicle 0.4: standalone animations and animated TADs
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude project thread "Chronicle animation skill", 20 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0002, RFC-0003, RFC-0004]
author: Claude Code, for Jacqueline Dean
created: 2026-10-20
---

# RFC-0005 chronicle 0.4: standalone animations and animated TADs

## 1. Summary
chronicle's motion lives inside story pages: paintings develop, layers move, diagrams
step. None of it can leave the page. Version 0.4 adds a second skill,
`/chronicle:animation`, that makes one animation as files that play anywhere: a single
SVG, an HTML figure, a poster PNG, a GIF and an MP4.

**Decision: technical architecture diagrams (TADs) are a kind of the one animation skill,
not a separate skill.** An animation has a `kind`: `tad`, `diagram` or `scene`. The three
kinds share the step clock, the stage (title, captions, step strip), the theme, the
checks, the CLI and every export. They differ only in what Claude writes, so the TAD
specifics live in one reference file (`references/tad.md`) and one code package
(`core/motion/tad/`).

1. A `tad` kind: Claude writes components, groups, links and flows as data; code places
   them in tiers, routes every line around the boxes, draws icons, and plays the steps.
2. A `diagram` kind: an SVG in the story diagram format, played by element id. A story's
   diagram plays as it is.
3. A `scene` kind: a story drawing painted in watercolor that develops from sketch to
   color, keeps its moving layers and gains numbered callouts.
4. `chronicle animate new|check|build`, and the exports: SVG, HTML, PNG, GIF, MP4, WebM.

## 2. The need
**User scenario:** Jacqueline Dean asked for "a new skill/scripts/etc. specifically for
animations so I can create animations similar to ones from the existing story skill, but
they should be standalone to allow easy integration into existing content across various
platforms", plus "a variation specifically for creating TAD (technical architecture
diagrams) animations", and asked Claude to decide between a separate TAD skill and a
type of the generic skill.

Story motion today needs the page's runtime script, its stylesheet and its scroll
position. A slide, a README, a Confluence page or a Slack message has none of those.

**Done means:**
- One `animation.json` builds to an SVG that plays with no script in a browser, inline
  in HTML and as an `<img>`, and shows the whole picture where motion is off.
- The same build writes an HTML figure to paste, a poster, a GIF and an MP4.
- A TAD is written as data with no coordinates, and builds with no overlapping boxes.
- Three examples (TAD, diagram, scene) check with no warnings and build.
- The four quality gates pass. Version 0.4.0 is in the plugin and marketplace manifests.

## 3. Interview record
No interview was held; the request asked Claude to decide and build.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | A separate TAD skill or a type of the animation skill? | Decide | A kind of one skill (4.1) |
| 2 | Which platforms? | "various platforms" | SVG, HTML, PNG, GIF, MP4, WebM; table in `references/formats.md` |
| 3 | Similar to which story animations? | The story skill's | Packets, focus and dims from flows and diagrams; develop and layer motion from plates |
| 4 | Version | Bump on code changes (memory) | 0.3.0 to 0.4.0 |
| 5 | Build ahead of approval? | Yes, as for chronicle so far | Built in this PR; this RFC awaits approval |

## 4. Proposal

### 4.1 One skill, three kinds
A separate TAD skill would repeat the brief, the step rules, the timing, the build and
look loop, the formats table and the delivery steps, which are about four fifths of the
skill's text and all of the CLI and export code. Two skills that both answer "animate
this" would also split the trigger: a request for "an animated diagram of our services"
fits both. One skill with a `kind` keeps one description to trigger, one place to learn
steps and formats, and one command. The skill's description names TADs, so requests for
architecture animations still load it.

TADs still get their own depth: a reference file with every node kind, group style,
state and layout rule, and a package with the spec reader, layout, router and drawing.

### 4.2 The animation file
`animation.json` holds `meta` (title, description as alt text, kicker, credit, sources),
the story `theme` (concept, palette, dark, fonts), `frame` (six sizes or pixels; title,
captions, step strip, background, light or dark), `timing` (pace, lead, hold, loop), the
kind's object, and `steps`. A step has one caption and actions: `show`, `hide`, `draw`,
`flow`, `focus`, `pulse` and, for TADs, `state`. Code times each step from its caption's
reading time (190 words a minute), a 2.2-second floor and what it plays.

### 4.3 The engine: CSS keyframes on one clock
Every moving part is a CSS keyframe track that spans the whole loop with no delay of its
own. Only opacity, the dash offset, `translate`, `rotate` and `scale` move. So:
- one negative `animation-delay` seeks the whole figure, which is how frames are captured;
- the file plays as an image in a README or a wiki, where scripts never run;
- each track's resting value is the final picture, so reduced motion, a slide editor or
  a print shows every part;
- the theme is scoped to the animation's own class, so two animations on one page, or one
  inside a story page, keep their colors.

### 4.4 TADs
- **Spec:** nodes (`kind` picks one of 23 icons; `tech`, `replicas`, `tone`), groups
  (`zone`, `cluster`, `boundary`, `external`, nested by `parent`), edges (`sync` or
  `async`, labels), flows (node paths along edges, either direction), an optional legend.
  Errors name the fix and suggest the nearest id or kind.
- **Layout:** tiers by longest path along the edges; lanes by packing each group as a
  block, seating the most linked item first, in the free rows nearest the parts it links
  to, then moving lone nodes to the middle of their neighbors. Groups never overlap.
  `tier` and `lane` override. A diagram shrunk under 62 percent warns.
- **Routing:** orthogonal lines with rounded corners from side ports, channels chosen
  clear of other boxes, parallel lines spread onto tracks, labels on the longest level
  run, filled heads for requests and open heads for events.
- **Motion:** parts appear in turn and pop; lines draw on through a mask once both ends
  are in, and their labels fade in after; packets with a trail run each hop of a flow
  and light the line; focus dims the rest; states add rings and tags (NEW, LEGACY, DOWN,
  PLANNED) or badges (check, !, ×).

### 4.5 Exports
| File | How it is made |
| --- | --- |
| `animation.svg` | the stage and the kind's figure in one SVG, fonts by Google Fonts `@import` |
| `embed.html`, `index.html` | a `<figure>` with a CSS-only pause button (WCAG 2.2.2), caption and steps list |
| `poster.png`, `steps.png` | frames from a local headless Chromium over its DevTools pipe |
| `animation.gif` | chronicle's own GIF encoder in NumPy: one palette with the 48 most frequent colors kept exact, changed-box frames, merged still frames |
| `animation.mp4` | frames piped to the local ffmpeg program (H.264, yuv420p, faststart) |
| `animation.webm` | OpenCV's VP9 writer, when ffmpeg is missing or asked for |

The checkout TAD example (10 nodes, 4 groups, 9 edges, 3 flows, 5 steps) is a 26-second
loop: an 88 KB SVG, a 630 KB GIF at 960 pixels and 15 frames a second, and a 431 KB MP4
at 1280 x 720 and 30 frames a second. Capturing its 781 frames took 3 minutes 12 seconds
in the build container.

### 4.6 Commands and shared code
- `chronicle animate new FOLDER --kind tad|diagram|scene` writes `animation.json`,
  `facts.json` (and `drawing.svg` for a diagram) and git-ignores the runs folder.
- `chronicle animate check ANIMATION` validates the shared keys, the kind, every id a
  step names, fact tokens and the theme.
- `chronicle animate build ANIMATION --formats ... --fps --gif-fps --gif-width --theme`
  paints a scene once (unchanged art is kept), renders, and captures.
- Story code reused, not copied: the theme gains `scoped()` (tokens under a class), facts
  gain `fill()`, the diagram classes move to a shared stylesheet part, and painting and
  run-folder code move from `main.py` to `art.py` and `runs.py` for both commands.

## 5. Alternatives considered
- **A separate `/chronicle:tad` skill.** Rejected for 4.1: it repeats most of the skill
  and splits the trigger. Kept open as question 10.1.
- **SMIL animation (`<animate>`).** Rejected: it cannot be seeked by one CSS variable for
  capture, and reduced motion does not stop it without script.
- **JavaScript or Lottie.** Rejected: scripts do not run in an SVG shown as an image,
  in GitHub, wikis or slides; Lottie needs a player.
- **A layout library (Graphviz, ELK, Mermaid).** Rejected: a runtime dependency, and
  their output does not know groups as nested blocks with labels.
- **Playwright or Puppeteer for frames.** Rejected: a runtime dependency. The installed
  browser's DevTools pipe needs none.
- **Pillow or imageio for GIF.** Rejected: a new dependency; NumPy is already used.

## 6. Risks and objections
- **Model-written drawings.** Diagrams pass the story's allowlist sanitizer; TAD text is
  escaped where it is written; ids are checked against a pattern.
- **Local programs.** Chromium and ffmpeg run as argument lists with no shell, on the
  built files only. As root (containers) Chromium needs `--no-sandbox`.
- **Fonts in an SVG shown as an image** do not load; system fonts stand in. The formats
  reference says so and points to the HTML figure where type matters.
- **Capture time** grows with length and frame rate (about 0.25 seconds a frame).
- **A crowded TAD** shrinks its text; `build` warns under 62 percent and the skill reads
  `steps.png` before sharing.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. chronicle 0.3.0 becomes 0.4.0.
**Constitution check:**
- Principle 1 (scripts compute, Claude writes): kept. Claude writes the TAD as data and
  the steps; layout, routing, timing and encoding are code.
- Principle 2 (every number has a source): kept. Captions, labels and drawings take fact
  tokens, and bare numbers warn.
- Principle 3 (local and private): **tension**, as in RFC-0004. The SVG imports its fonts
  from Google Fonts, and frame capture opens it in a local browser, which loads them. No
  gathered data leaves the machine. Open question 10.2.
- Principle 4 and the guardrails: NumPy and OpenCV, already used for painting and pending
  RFC-0002, now also encode GIFs and frames. Chromium and ffmpeg are optional programs the
  user already has; `build` says what is missing and writes what it can.

## 8. Cross-repo contract
N/A, internal.

## 9. Further optimizations, not built here
| # | Opportunity | Evidence | Effort |
| --- | --- | --- | --- |
| 1 | An `animation` block in story pages, so a page embeds its own animation | the scene example reuses a story plate by path | small |
| 2 | Capture frames in two browser tabs at once | 0.25 seconds a frame | small |
| 3 | Subset and embed the fonts in the SVG so an `<img>` shows the theme's type | fonts fall back in an image | medium |
| 4 | A sequence diagram kind (lifelines and messages) for the same TAD data | flows already list ordered hops | medium |
| 5 | Import a TAD from a Mermaid flowchart or a C4 model | teams keep diagrams in those | medium |
| 6 | A Lottie export for app screens | not asked for | large |

## 10. Open questions
1. Approve TADs as a kind of the one animation skill, or split a `/chronicle:tad` skill?
2. Accept the SVG's Google Fonts `@import` under principle 3, or embed fonts (question 9.3)?
3. Accept ffmpeg as an optional system program for MP4, with WebM through OpenCV when it
   is missing?
4. Which of section 9 come next?
