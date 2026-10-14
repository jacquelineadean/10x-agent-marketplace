---
name: story
description: Build an illustrated, interactive story page (a claude.ai Artifact) from a brief plus facts gathered from connected tools such as GitHub, Jira, Confluence, Datadog or PagerDuty, or from pasted notes and files. Use for project status and history, portfolio or quarterly reviews, launch recaps, incident reviews, team updates, research briefs, or any request to turn content into a beautiful, interactive, illustrated page with charts. The page gets watercolor plates painted in code, editorial charts, scrollytelling and a source behind every number.
---

# chronicle: illustrated story pages

chronicle makes one long-form web page in the manner of a New York Times graphics feature:
a narrative in chapters, watercolor plates painted by code, charts that respond to the
reader, and a sticky bar that maps reading progress. Every number on the page comes
from a facts file and shows its source on hover.

The work splits so the model writes and code computes:

| Step | Who | Output (in the run folder) |
| --- | --- | --- |
| 1. Brief | you, with the user | a few lines in your head, nothing written |
| 2. Gather | `chronicle-gatherer` subagent, or you for pasted content | `facts.json` |
| 3. Write | you | `story.json` |
| 4. Build | `chronicle build` (check, derive, paint, render) | `build/artifact.html`, `build/art/*.webp` |
| 5. Publish | you, with the Artifact tool | a private claude.ai link |

Run folder: `chronicle-runs/<short-slug>/` under the working directory unless the user names
another. Never write gathered company data into a git repository; add the folder to
`.gitignore` if the working directory is a repository and the entry is missing.

## 1. Settle the brief

Find out, asking only what the request leaves open (one AskUserQuestion, at most 4 questions):

- **Audience and forum**: who reads it and where (steering committee, all-hands, QBR, a PR).
- **The point**: the one decision or takeaway the page must land. It becomes the hero dek.
- **Window**: the period the story covers; default from project start to today.
- **Sources**: which connected tools, files or pasted notes to use.

When the user asks for a demonstration or mock data, invent a plausible organisation and
say so on the page: the byline and colophon both state that the data is invented.

## 2. Gather facts

Read `references/facts.md` for the file format and `references/sources.md` for what to
pull from each tool.

- **Connected tools**: delegate to the `chronicle-gatherer` subagent. Give it the brief, the
  window, the tools to query and the run folder. It writes `facts.json` and returns a short
  summary. Raw tool output stays in the subagent, never in this conversation.
- **Pasted notes and files**: extract the facts yourself into the same format.
- Each number is a record with `value`, `unit`, `source` and a `note` that says what it
  measures. Series are plain arrays. Averages, ratios, percent changes and forecasts go in
  the `derive` table, so code computes them; never do arithmetic in your head.
- Missing numbers stay missing. Write the sentence without the number, or ask the user.

## 3. Write the story

Read `references/story-format.md` (structure and every block), `references/voice.md`
(how the page reads) and `references/outlines.md` (chapter plans for common forums).
Pick the illustration metaphor with `references/scenes.md`.

- Numbers appear only as tokens: `{{migration.share_now}}`, or `{{plan.forecast_finish|date}}`.
  Chart data points at series with `"@delivery.deploys_per_week"`.
- One claim per chapter, stated in its title. Each chapter carries at least one plate or figure.
- Prefer an interactive figure where the reader would ask "what if" or "when": a stepper
  for an incident, a model with sliders for a forecast or a cost, scrollytelling for a
  trend with turning points.

## 4. Build

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/chronicle" build chronicle-runs/<slug>/story.json
```

The command checks the story, runs the `derive` table, paints every scene that changed
(2 to 4 seconds each) and writes `build/artifact.html`, `build/index.html` and
`build/publish-files.json`. Fix every error. Treat each warning about an unsourced number
as a sentence to rewrite with a token. `chronicle check <story>` validates without
painting; `chronicle motifs` lists presets and motifs.

The script runs through `uv` with NumPy and OpenCV when `uv` is installed. Without `uv`
it needs Python 3.11+ with `numpy` and `opencv-python-headless`; if painting is not
possible, say so and offer `build --no-paint`, which renders with plates left out.

## 5. Publish

- Ask once before publishing data gathered from company systems: the Artifact is private
  to the user, but it is hosted on claude.ai.
- Publish `build/artifact.html` with the Artifact tool. Pass `files` as the map in
  `build/publish-files.json` (published path to local path), `icon: "chart"` and a
  one-sentence `description`.
- To update, rebuild and republish the same file path (or the artifact `url` in a later
  conversation); the link stays the same.
- Optional check before publishing: one screenshot at desktop and phone width.

## 6. Report

Reply with the link, one line on what the page covers, and any facts that were missing.

## Files

- `references/story-format.md`: the story file, every block type, tokens and formats.
- `references/facts.md`: the facts file, provenance and the `derive` functions.
- `references/sources.md`: what to gather from GitHub, Jira, Confluence, Datadog, PagerDuty.
- `references/outlines.md`: chapter plans for status reports, reviews, incidents, launches.
- `references/scenes.md`: presets, the motif language for new paintings, and metaphors.
- `references/voice.md`: the page's writing rules.
- `${CLAUDE_PLUGIN_ROOT}/examples/keystone/`: a complete worked example with invented data.
