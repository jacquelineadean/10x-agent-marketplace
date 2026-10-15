---
id: RFC-0003
title: chronicle 0.2: pages designed for their subject
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude Code session, 15 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0002]
author: Claude Code, for Jacqueline Dean
created: 2026-10-15
---

# RFC-0003 — chronicle 0.2: pages designed for their subject

## 1. Summary
chronicle 0.1 gave every page the same look: a bridge metaphor, three fixed fonts, a plain
progress bar and landscape paintings. Version 0.2 lets each page take its identity from its
subject. Four changes do this:
1. A `theme` in the story sets palette, fonts, a progress device, chapter marks and a stat style.
2. Claude draws each painting as SVG; a new ink-and-wash painter paints it.
3. Six new blocks cover places, processes, mechanisms and teaching: `tilemap`, `flow`,
   `diagram`, `quiz`, `checklist` and `widget`.
4. The skill gains a design pass (`identity.md`) and drawing rules (`illustration.md`).

The Keystone example is rebuilt around the order platform: parcels, packing slips, a
warehouse, a conveyor progress bar and a receipt for the hero numbers. A second example,
`examples/onboarding/`, is a coffee roaster's first-week handbook with a quiz, a checklist
and a custom widget.

## 2. The need
**User scenario:** Jacqueline Dean compared the Keystone page with a retailer's page whose
progress bar was a tape measure and whose map showed its stores over time. Keystone's
landscapes and bridge metaphor could have illustrated any project. She wants pages for
project updates, product launches, onboarding and training handbooks, and guides to
podcasts or talks, each designed for its content.
**Done means:**
- Two example pages with different subjects share no illustration, palette, font set,
  progress device or chapter mark.
- The skill tells Claude how to derive each of those from the subject.
- The four quality gates pass. Version 0.2.0 is in the plugin and marketplace manifests.

## 3. Interview record
No interview was held; the request was explicit and asked for autonomous iteration.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | What changes? | Illustrations and theme tailored to the content, for this page and future ones | From request |
| 2 | Which page types? | Project updates, feature releases, onboarding and training, guides from input | From request |
| 3 | Reference | A retailer page with a tape-measure progress bar and a store map over time | From request |
| 4 | Keep watercolor? | Yes, drawn for the subject instead of landscape presets | Assumed, open |
| 5 | Custom code per page? | Allowed as a checked widget when no block fits | Assumed, open (7) |

## 4. Proposal

### 4.1 Theme
`story.theme` holds:
- `palette`: paper, ink, accent (the new thing), legacy (the old thing), status colors, six
  series colors and named colors.
- `fonts`: display, body, ui, hand and mono roles, chosen from 60 Google Fonts families in
  `assets/fonts.json`, each with its valid weight axes.
- `progress`: arches, track (with an icon and a line: belt, road, rail, dashed), tape,
  flags, clock or steps.
- `chapter_mark`: arch, label, tag, sign, badge, flag, step, plain or none, with a prefix and
  a number format.
- `stats`: rule, cards, receipt or ticket.

Code derives the dark palette and raises any text color that misses WCAG AA contrast
against its background. An unknown font or weight is an error at check time.

### 4.2 SVG drawings and the ink-and-wash painter
Claude writes plain SVG (`path`, `rect`, `circle`, `ellipse`, `line`, `polyline`,
`polygon`, `g`, `use`, `defs`, `symbol`, `linearGradient`, `text`). A standard-library
reader flattens paths, arcs and transforms into polygons. The painter turns:
- each fill into a loose wash with rim darkening, granulation and a shading gradient away
  from the light;
- each stroke into a pen line that wavers and overshoots its corners;
- `<text>` into live overlay labels that may hold fact tokens.

`data-*` hints set paint, line, shade, hatch and motion. Moving parts (`drift`, `cross`,
`spin`, `bob`, `sway`, `pop` and others) paint on their own sheet. The 0.1 presets and
motifs stay for pages that want scenery.

### 4.3 New blocks
| Block | Purpose |
| --- | --- |
| `tilemap` | US states or custom tiles, with frames, a slider and Play, markers and a live readout |
| `flow` | A process as steps, compared across two or more states, with a token that travels |
| `diagram` | A mechanism drawn in SVG, sanitized by an allowlist, with steps that dim parts |
| `quiz` | Questions with explanations and a closing result |
| `checklist` | Tasks with a progress meter, kept in the reader's browser when storage works |
| `widget` | A script Claude writes for one page, run as `function (root, data, kit)` |

### 4.4 Runtime split
The 0.1 single stylesheet and script are split into numbered parts under `assets/css/` and
`assets/js/`, joined at build time inside one IIFE. Page behavior does not change.

## 5. Alternatives considered
- **More presets per industry.** Rejected: a fixed library cannot cover every subject, and
  pages that share presets look alike.
- **Image-generation models for drawings.** Rejected for the reasons in RFC-0002: not
  deterministic, no exact state.
- **Let Claude write raw page HTML for custom figures.** Rejected: the widget contract keeps
  the page's escaping, theme and facts; free HTML would bypass all three.

## 6. Risks and objections
- **Drawing quality depends on Claude's SVG.** Mitigation: `illustration.md` gives
  composition and perspective rules, and the skill requires looking at every painting.
- **Widget scripts are model-written code in the page.** Mitigation: `chronicle check`
  refuses `innerHTML`, `eval`, `fetch`, storage, cookies, `postMessage` and URLs; styles
  refuse `@import` and `url()`. Widgets read only their block's data.
- **Diagrams carry Claude-written SVG.** Mitigation: an allowlist sanitizer drops scripts,
  styles, links and event attributes, and prefixes every id.
- **More fonts per page.** The hand and mono roles load only when a page uses them.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. chronicle 0.1.0 becomes 0.2.0.
**Constitution check:**
- Principle 1 (scripts compute, Claude writes): **tension.** A widget is code Claude writes
  that computes in the reader's browser. Proposed reading: widgets may compute
  presentation (a slider's model, a drill) from facts in the block's data; facts and derived
  numbers still come from the facts file and the derive table.
- Principle 2 (every number has a source): extended to drawing labels and diagram text,
  which take fact tokens and get the same warning for typed numbers.
- Principles 3 to 5 and the guardrails: unchanged. No new runtime dependency.

## 8. Cross-repo contract
N/A, internal.

## 9. Out of scope
- World and country maps beyond US states and custom tile grids.
- Photographs turned into paintings.
- A browser test suite for the page runtime (checked by hand in Chromium for this change).

## 10. Open questions
1. Approve widgets under the reading of principle 1 in section 7?
2. Keep the 0.1 landscape presets, or remove them in a later version?
