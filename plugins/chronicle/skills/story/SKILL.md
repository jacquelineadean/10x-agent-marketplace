---
name: story
description: Build an illustrated, interactive story page (a claude.ai Artifact) whose look is made for its subject, from a brief plus facts gathered from connected tools such as GitHub, Jira, Confluence, Datadog or PagerDuty, or from pasted notes, files, transcripts and documents. Use for project status and history, migrations, portfolio or quarterly reviews, product and feature launches, incident reviews, onboarding handbooks and training, guides to a podcast, talk or book, team updates and research briefs, or any request to turn content into a beautiful, interactive, illustrated page with charts. The page gets watercolor illustrations drawn for its subject and painted in code, a theme and progress bar from the subject's world, editorial charts, maps, flows, diagrams, quizzes, and a source behind every number.
---

# chronicle: illustrated story pages made for their subject

chronicle makes one long-form web page in the manner of a New York Times graphics feature
or a New Yorker spread: a narrative in chapters, ink-and-watercolor illustrations of the
subject's own objects and places, charts and figures that respond to the reader, and a
sticky progress bar shaped like something from the subject's world. Every number on the
page comes from a facts file and shows its source on hover.

The test of a good page: it could only be about this subject. A retailer's page measures
progress with a tape measure; a golf club's handbook marks chapters with flags; a parcel
platform's page rides a parcel along a conveyor. Generic landscapes and stock metaphors
fail the test.

The work splits so the model writes and draws, and code computes and paints:

| Step | Who | Output (in the run folder) |
| --- | --- | --- |
| 1. Brief | you, with the user | a few lines in your head |
| 2. Gather | `chronicle-gatherer` subagent, or you for pasted content | `facts.json` |
| 3. Design the identity | you | `theme` and a list of paintings and figures |
| 4. Draw | you | `art/*.svg`, `diagrams/*.svg`, optional `widgets/*` |
| 5. Write | you | `story.json` |
| 6. Build | `chronicle build` (check, derive, paint, render) | `build/artifact.html`, `build/art/*.webp` |
| 7. Publish | you, with the Artifact tool | a private claude.ai link |

Run folder: `chronicle-runs/<short-slug>/` under the working directory unless the user names
another. Never write gathered company data into a git repository; add the folder to
`.gitignore` if the working directory is a repository and the entry is missing.

## 1. Settle the brief

Find out, asking only what the request leaves open (one AskUserQuestion, at most 4 questions):

- **Audience and forum**: who reads it and where (steering committee, all-hands, new hires, a PR).
- **The point**: the one decision, takeaway or skill the page must land. It becomes the hero dek.
- **Window or scope**: the period or the material the page covers.
- **Sources**: which connected tools, files, transcripts or pasted notes to use.
- **Brand**: colors, logo shapes or typefaces the organization uses, if any.

When the user asks for a demonstration or mock data, invent a plausible organization and
say so on the page: the byline and colophon both state that the data is invented.

## 2. Gather facts

Read `references/facts.md` for the file format and `references/sources.md` for what to
pull from each tool.

- **Connected tools**: delegate to the `chronicle-gatherer` subagent. Give it the brief, the
  window, the tools to query and the run folder. It writes `facts.json` and returns a short
  summary. Raw tool output stays in the subagent, never in this conversation.
- **Pasted notes, files, transcripts**: extract the facts yourself into the same format.
- Each number is a record with `value`, `unit`, `source` and a `note` that says what it
  measures. Series are plain arrays. Averages, ratios, percent changes and forecasts go in
  the `derive` table, so code computes them; never do arithmetic in your head.
- Missing numbers stay missing. Write the sentence without the number, or ask the user.

## 3. Design the identity

Read `references/identity.md` and do its design pass before writing anything else:

- List the subject's objects, places, number-carrying artifacts, rituals and brand.
- Write `story.theme`: palette (`accent` for the new thing, `legacy` for the old), fonts
  from the list, a progress device, a chapter mark and a stat style, each taken from the
  subject's world.
- Plan one painting for the hero and at most one per chapter, each a concrete object or
  scene that shows the chapter's claim at its real state.
- Pick the figures the material calls for: `flow` for a process, `tilemap` for places,
  `diagram` for a mechanism, `quiz` and `checklist` for teaching, `model` for a what-if,
  a `widget` only when nothing else fits.

## 4. Draw

Read `references/illustration.md`. Draw each painting as an SVG file in `art/`: shapes back
to front, ink outlines, fills in muted pigment colors, `data-shade` for volume, glazed cast
shadows, `<text>` labels (which may hold fact tokens), `data-anchor` points for hotspots and
at most one or two moving layers. Draw diagrams as SVG in `diagrams/` with the classes in
`references/story-format.md`. Write widgets with `references/widgets.md`.

Run `chronicle build` early and look at each `build/art/<key>.webp` with the Read tool. Fix
objects that do not read at a glance, flat clip-art looks and collisions, then build again.

## 5. Write the story

Read `references/story-format.md` (structure and every block), `references/voice.md`
(how the page reads) and `references/outlines.md` (chapter plans for status reports,
launches, onboarding, guides, incidents and reviews).

- Numbers appear only as tokens: `{{migration.share_now}}`, or `{{plan.forecast_finish|date}}`.
  Chart data points at series with `"@delivery.deploys_per_week"`.
- One claim per chapter, stated in its title. Each chapter carries at least one painting or figure.
- Keep the metaphor consistent in every caption, alt text, spot and title once the
  identity is chosen; do not mix it with another.
- Prefer an interactive figure where the reader would ask "what if", "where" or "how": a
  stepper for an incident, a flow for a journey, a tile map for a rollout, a model with
  sliders for a forecast or a cost, scrollytelling for a trend with turning points.

## 6. Build

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/chronicle" build chronicle-runs/<slug>/story.json
```

The command checks the story, the theme, every drawing and diagram and widget script; runs
the `derive` table; paints every scene that changed; and writes `build/artifact.html`,
`build/index.html` and `build/publish-files.json`. Fix every error. Treat each warning
about an unsourced number as a sentence or label to rewrite with a token.
`chronicle check <story>` validates without painting; `chronicle motifs` lists the
landscape presets and motifs.

The script runs through `uv` with NumPy and OpenCV when `uv` is installed. Without `uv`
it needs Python 3.11+ with `numpy` and `opencv-python-headless`; if painting is not
possible, say so and offer `build --no-paint`, which renders with plates left out.

Before publishing, look at the page: one screenshot at desktop width and one at phone
width if a browser is available, or at least every painting.

## 7. Publish

- Ask once before publishing data gathered from company systems: the Artifact is private
  to the user, but it is hosted on claude.ai.
- Publish `build/artifact.html` with the Artifact tool. Pass `files` as the map in
  `build/publish-files.json` (published path to local path), `icon: "chart"` and a
  one-sentence `description`.
- To update, rebuild and republish the same file path (or the artifact `url` in a later
  conversation); the link stays the same.

## 8. Report

Reply with the link, one line on what the page covers, and any facts that were missing.

## Files

- `references/identity.md`: designing the page for its subject: palette, fonts, progress
  devices, chapter marks, stat styles, and worked identities.
- `references/illustration.md`: drawing SVG for the ink-and-watercolor painter.
- `references/story-format.md`: the story file, every block type, tokens and formats.
- `references/facts.md`: the facts file, provenance and the `derive` functions.
- `references/sources.md`: what to gather from GitHub, Jira, Confluence, Datadog, PagerDuty.
- `references/outlines.md`: chapter plans for status reports, launches, onboarding,
  guides, incidents and reviews.
- `references/widgets.md`: writing a custom figure when no block fits.
- `references/voice.md`: the page's writing rules.
- `${CLAUDE_PLUGIN_ROOT}/examples/keystone/`: a status page with invented data: an
  order-platform migration with its own theme, seven painted SVG drawings, a flow, a tile
  map and an incident diagram.
- `${CLAUDE_PLUGIN_ROOT}/examples/onboarding/`: a first-week handbook with invented data:
  a coffee roaster's theme, two drawings, a flow, a custom tile map, a widget, a checklist
  and a quiz.
