---
id: RFC-0004
title: chronicle 0.3: no two pages alike
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude project thread "Unique designs for chronicle story", 20 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0002, RFC-0003]
author: Claude Code, for Jacqueline Dean
created: 2026-10-20
---

# RFC-0004 — chronicle 0.3: no two pages alike

## 1. Summary
chronicle 0.2 lets a theme set palette, fonts, a progress device, chapter marks and a stat
panel. Three pages built since then show where that stops: each one needed hand-written
CSS and scripts to look like its subject, and shared code still carried the first
example's copy. Version 0.3 makes the design start from a written concept, adds four
theme parts that pages had to hand-build, checks that a page does not look like another,
and adds two commands that save steps on every run.

1. `theme.concept`: one sentence naming the world the page borrows from, taken from the
   user's inputs first. `chronicle check` warns when it is empty.
2. Four theme parts: a `route` progress device along a path the page draws, a drawn
   `icon_path`, a `surface` (paper texture, corners, how plates hang) and `words` for every
   control and heading.
3. A sameness review in `chronicle check`: warnings for stock themes and for themes that
   share three features with a bundled example or a sibling run.
4. `chronicle new` starts a run folder; `chronicle shoot` screenshots the built page at
   desktop and phone width.
5. Fixes: shared code no longer names Keystone or "the monolith"; a widget used twice ships
   its stylesheet once; the `cup` and `book` icons the runtime draws are now accepted.

## 2. The need
**User scenario:** the request asked for each page's design to be unique to its inputs,
prompt or derived theme, pointing at three pages: a golf-simulator employee handbook, a
podcast episode guide and an Ossabaw Island field guide. All three were read in full for
this RFC.

| Page | How it was built | What it needed beyond chronicle 0.2 |
| --- | --- | --- |
| Golf-simulator handbook "Yardage Book" (241 KB, 20 files) | chronicle 0.1 runtime plus a hand-written "Yardage Book" layer of about 1,000 lines (335 of CSS, about 700 of script) | a course bar of nine flags, quizzes played as holes with golf scores, a launch-monitor calibration drill, a scorecard, golf words on every control |
| Podcast guide "Four Mental Models, Illustrated" (167 KB, 10 files) | written by hand outside chronicle | a 45-minute interview clock with phases, red-pen notes that pop onto the painting, a marker hand font, over 20 custom figures |
| Ossabaw field guide (432 KB, 120 files) | chronicle 0.2 with 6 widgets | a trail map in the top bar (drawn by a widget that hides the progress bar), a map tour, habitat views; the habitat stylesheet shipped three times |

Two faults were shared. The base stylesheet's comments called the accent "ultramarine:
the new platform" and the legacy color "burnt sienna: the monolith", and a page with no
theme took the first example's 0.1 look (ultramarine, Instrument Serif, bridge arches).
The savings model printed "Monolith switched off" and "Keystone only" on any page.

**Done means:**
- A theme can say, without a widget: a route drawn for the subject, its own icon, its
  paper, its corners, how paintings hang, and the words of every control.
- `chronicle check` warns on an empty concept, a stock theme and a theme like another page.
- The three bundled examples pass the sameness review against each other.
- No runtime file names an example's subject.
- The four quality gates pass. Version 0.3.0 is in the plugin and marketplace manifests.

## 3. Interview record
No interview was held; the request asked for autonomous iteration.

| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | What should drive the design? | User-provided inputs, the prompt and/or a derived theme | From request; sets the concept order in 4.1 |
| 2 | Reference pages | Golf handbook, podcast guide, Ossabaw field guide | From request; section 2 |
| 3 | Scope | Improve the skill and plugin; list optimizations | From request; section 9 lists what is not built here |
| 4 | Version | Bump when the plugin or skill changes | From request; 0.2.0 to 0.3.0 |
| 5 | Fail or warn on a page like another? | Warn | Assumed, open (10.1) |

## 4. Proposal

### 4.1 The concept
`theme.concept` is one sentence: the world the page borrows from and where it came from.
The skill takes it from the first of these that gives one:
1. what the user supplied: brand colors, logos, typefaces, screenshots, files;
2. the words of the request, where the format noun sets the structure ("field guide",
   "handbook", "episode visualization", "postmortem");
3. the material's world: its objects, places and rituals;
4. the page's point as a picture.

Every other theme choice follows from the concept. The skill also asks for one signature
figure per page: the interaction only this page would have.

### 4.2 Theme parts
| Key | Values | Replaces |
| --- | --- | --- |
| `progress.kind: route` with `path` | SVG path data in a 1000 x 40 box; stops at equal distances along it | Ossabaw's trail-map widget |
| `progress.icon_path` | SVG path data centered on 0,0 | the fixed icon list for subjects with their own token |
| `surface.texture` | plain, ruled, grid, dots | hand CSS for notebook or blueprint paper |
| `surface.corners` | square, soft, round (scales every radius through `--round`) | hand CSS |
| `surface.frame` | none, mat, tape | hand CSS for prints and field-notebook plates |
| `words` | 17 keys: sources, source, show_numbers, hide_numbers, step, of, back, next, play, pause, question, next_question, see_score, score, try_again, done, overview | the golf layer's rewritten quiz chrome |

Paths accept path commands, numbers, commas and spaces only. Words are plain text of 1 to
40 characters. Both are escaped where they are written.

### 4.3 The sameness review
A theme has six features: type (display and body faces), accent, paper, progress device,
chapter mark and stat panel. `check` warns when two features are chronicle's defaults, and
when three or more match a bundled example or one of up to 40 sibling run folders (accent
within 6 percent RGB distance, paper within 2.5 percent). It warns; it does not fail.

### 4.4 Commands
- `chronicle new FOLDER [--title]` writes `story.json` (with an empty concept, so `check`
  asks for one) and `facts.json`, makes `art/`, `diagrams/`, `widgets/`, and adds the runs
  folder to `.gitignore` in a git working directory.
- `chronicle shoot STORY [--browser PATH]` opens `build/index.html#still` in an installed
  headless Chromium or Chrome at 1280 and 390 pixels wide and writes PNGs to
  `build/shots/`. `#still` makes the runtime skip arrival animations so paintings show in
  color. Headless Chromium will not open a window narrower than 500 pixels, so the phone
  shot frames the page at 390 pixels inside a 500-pixel window.

### 4.5 Examples
Keystone and onboarding gain a concept; onboarding gains a dotted surface, mats and coffee
words ("Cup 1 of 5"). The quarterly support-desk example, which had no theme, becomes a
lighthouse keeper's log: a route along a coastline walked by a drawn lighthouse, ruled
paper, taped plates, watch badges and a ticket stub.

## 5. Alternatives considered
- **A preset per page type** (handbook, field guide, podcast). Rejected for the reason in
  RFC-0003: pages sharing a preset look alike.
- **Fail the build on a page like another.** Rejected for now: a brand can force a
  palette, and an owner may want a family of pages. Open question 10.1.
- **Playwright for screenshots.** Rejected: it adds a runtime dependency. The installed
  browser's own `--screenshot` flag needs none.

## 6. Risks and objections
- **Model-written path data in the page.** Mitigation: an allowlist pattern (commands,
  numbers, separators) and a required leading M; it is set as an attribute, never markup.
- **The review compares only six features.** Two pages can pass and still feel alike.
  Mitigation: the skill's concept and signature figure steps, and the screenshots.
- **`shoot` runs a local program.** Mitigation: an argument list with no shell; it opens
  only the built page file. As root (containers) it adds `--no-sandbox`, which Chromium
  requires there.

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. chronicle 0.2.0 becomes 0.3.0.
**Constitution check:**
- Principle 1 (scripts compute, Claude writes): unchanged. The review is code.
- Principle 2 (every number has a source): unchanged.
- Principle 3 (local and private): **tension.** `shoot` opens the page in a local browser,
  which loads the page's Google Fonts, as opening `index.html` already does. No gathered
  data leaves the machine. Open question 10.2.
- Principle 4 and the guardrails: unchanged. No new runtime dependency; `shoot` uses a
  browser already installed and fails with a message when there is none.

## 8. Cross-repo contract
N/A, internal.

## 9. Further optimizations, not built here
| # | Opportunity | Evidence | Effort |
| --- | --- | --- | --- |
| 1 | Ship only the CSS and script parts a page's blocks use | Ossabaw page is 442 KB; most is unused figure code | medium |
| 2 | Promote the map tour and plate views (tabs that switch layers and spots) from widgets to blocks | Ossabaw used 4 widgets for these two ideas | medium |
| 3 | A quiz tally: scores across a page's quizzes color the progress device and fill a closing scorecard | the golf layer built this by hand | medium |
| 4 | Plate notes that appear as the reader arrives (red-pen marks, pencil sums) | the podcast page built these by hand | small |
| 5 | A widget library under the runs folder, so a drill written once is reused | habitat widget written for one page, used three times | small |
| 6 | Load only the font weights a page uses | each family loads every listed weight | small |
| 7 | Share the painting cache across runs, keyed by drawing hash | repainting identical drawings in a new folder | small |
| 8 | Redraw the quarterly hero as a harbor in SVG | its valley preset predates the lighthouse concept | small |
| 9 | A browser test suite using the `shoot` setup | RFC-0003 out of scope item | medium |

## 10. Open questions
1. Keep the sameness review as warnings, or fail the build when a page copies an example?
2. Accept `shoot` loading Google Fonts under principle 3, or block the network and shoot
   with fallback fonts?
3. Which of section 9 come next?
