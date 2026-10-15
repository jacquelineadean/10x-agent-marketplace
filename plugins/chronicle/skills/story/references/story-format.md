# The story file

`story.json` arranges facts into a page. It never holds a number in its text: numbers come
in through tokens that point into `facts.json`. Run `chronicle check story.json` after every
edit; it names each problem with its path, such as `chapters[2].blocks[1]`.

## Top level

```json
{
  "schema_version": 1,
  "meta": { ... },
  "sources": [ ... ],
  "art": { ... },
  "hero": { ... },
  "chapters": [ ... ]
}
```

| Key | Holds |
| --- | --- |
| `meta.title` | The page name: a short proper noun, also the browser title. Required. |
| `meta.kicker` | One line above the title: organization, subject, "Status on {{project.as_of\|date}}". |
| `meta.dek` | Two or three sentences under the title that state the point of the page. |
| `meta.byline` | List of short lines: who prepared it, for which forum, a demo notice if invented. |
| `meta.description` | One sentence for the gallery card and the meta description. |
| `meta.colophon` | Paragraphs for the end: how the page was made and what the data covers. |
| `theme` | The page's identity: palette, fonts, progress device, chapter marks, stat style. See `identity.md`. |
| `sources` | `[{"id", "label", "detail", "as_of"}]`; every fact's `source` names one `id`. |
| `art` | Named paintings, drawn as SVG and painted by `chronicle build`. See `illustration.md`. |
| `hero` | `{"art": key, "caption": text, "stats": [stat items], "stats_title", "stats_subtitle", "stats_style"}`; title and subtitle head a receipt or ticket |
| `chapters` | The story, in order. |

`facts.json` beside the story is read by default. `"facts_file": "other.json"` names another.

## Chapters

```json
{"id": "status", "short": "Status", "kicker": "Where the order path stands",
 "title": "Three steps moved", "dek": "optional italic line",
 "art": "counter", "caption": "plate caption", "at": 74, "blocks": [ ... ]}
```

`id` is the anchor (`#status`), letters, digits and dashes. `short` labels the chapter in
the sticky bar. `art` places a plate under the heading. `at` places the chapter on a
timed progress device (minutes into a podcast, say; see `identity.md`). The theme sets
how chapters are numbered and marked.

## Text, tokens and formats

Text fields accept `**bold**`, `*italic*`, `` `code` ``, `[link](https://...)`, `[link](#chapter-id)`
and blank lines between paragraphs. Everything else is escaped.

`{{path}}` inserts a fact; `{{path|format}}` picks a format. The value is shown with its
unit and wrapped in a span that names the source on hover.

| Format | 1284 | 99.95 % | 335000 $ | "2026-11-03" |
| --- | --- | --- | --- | --- |
| `auto` (default) | 1,284 | 99.95% | $335K | 2026-11-03 |
| `int` | 1,284 | 100% | | |
| `dec1`, `dec2` | 1,284.0, 1,284.00 | | | |
| `compact` | 1.3K | | $335K | |
| `signed` | +1,284 | +99.95% | +$335K | |
| `plain` (no unit) | 1,284 | 99.95 | $335K | |
| `pct` | 1,284% | | | |
| `date`, `month`, `year` | | | | 3 Nov 2026, Nov 2026, 2026 |

Units: `%`, `x` (shown as ×), `$` (compact money), `ms`, `min`, `pts`, `pp`, or any word
(`days`, `engineers`); `days`, `hours`, `sprints` and similar become singular for 1.

In figure specs, `"@path"` (the whole string) is replaced by the raw fact value, for
example a series: `"values": "@delivery.deploys_per_week"`.

`chronicle check` warns about any number typed into prose. Years are allowed; so are
numbers fused to a word, such as "95th" or "30-day".

## Blocks

Every block has a `type`. Most figures take optional `title`, `subtitle` and `source`
(a source `id`).

### prose
`{"type": "prose", "text": "...", "dropcap": true, "lead": false}`. Body text in the
reading column. Use `dropcap` on the first prose block of a chapter at most once or twice
per page.

### stats
`{"type": "stats", "title": "optional", "subtitle", "style", "items": [{"label", "value", "delta", "trend", "spark"}]}`.
A row of big numbers. `value` and `delta` are text with tokens; `trend` is `good`, `bad` or
`neutral` (colors the delta); `spark` is a series reference drawn as a sparkline.
Two to four items. `style` overrides the theme's: `rule`, `cards`, `receipt`, `ticket`.

### lesson
`{"type": "lesson", "title": "The lesson", "text": "...", "art": "keystone"}`. A boxed
takeaway with a small spot painting. One sentence or two; no more than one per two chapters.

### quote
`{"type": "quote", "text": "...", "who": "Name", "role": "role"}`. Only for words a person
said or wrote; never invent a quote about real people.

### chart
`{"type": "chart", "chart": KIND, "data": {...}, "format": {"y": FORMAT}, "unit": "ms", ...}`

| `chart` | `data` | Notes |
| --- | --- | --- |
| `line`, `area` | `{"x": [...], "series": [{"name", "values", "color"}]}` | `notes: [{"x", "text"}]` annotate turning points; `y_min`, `y_max` fix the axis |
| `stacked` | same as line | stacked areas; `"normalize": true` for shares that sum to 100 |
| `bars` | `{"categories": [...], "series": [...]}` | `"stacked": true` stacks; columns grow from zero |
| `burnup` | `{"x": dates, "scope": [...], "done": [...], "velocity": n, "growth": n}` | projects finish with a fan for a faster and a slower pace |
| `calendar` | `{"start": "YYYY-MM-DD" (a Monday), "values": [daily counts]}` | GitHub-style year grid; `unit` names the count |
| `multiples` | `{"x": [...], "items": [{"name", "values"}]}` | one small panel per item, shared scale; `target` draws a threshold |
| `slope` | `{"labels": [before, after], "items": [{"name", "before", "after", "better": "up" or "down", "format"}]}` | one panel per measure, each on its own scale |

`x` values are `YYYY-MM`, `YYYY-MM-DD` or plain labels such as `"09:41"`; points are
evenly spaced. `color` takes `accent` (the new thing), `legacy` (the old thing), `muted`,
`good`, `bad`, `s1` to `s6`, or a theme color name such as `kraft`; series are colored in
order otherwise. Never put two
measures with different units on one chart: use two charts or `slope`. Y formats:
`int`, `dec1`, `pct`, `pct1`, `pct2`, `money`, `money_k` (values in thousands), `ms`,
`compact`. Every chart gets hover readouts and a "Show the numbers" table.

### scrolly
`{"type": "scrolly", "chart": {chart spec without "type"}, "steps": [{"text", "focus": {"from", "to"}}], "source"}`.
The chart sticks while step cards scroll past; each step highlights the `x` range in
`focus`. Use for one trend with three to six turning points.

### timeline
`{"type": "timeline", "today": "YYYY-MM-DD", "eras": [{"from", "to", "label"}], "events": [{"date", "kind", "title", "text"}]}`.
`kind` is `milestone`, `launch`, `incident` or `planned`. The reader taps events on a track.

### stepper
`{"type": "stepper", "chart": {line chart spec}, "steps": [{"time", "title", "text", "focus": {"from", "to"}}]}`.
Back and Next walk through a sequence; the chart highlights each step's range. Made for
incident timelines and rollouts.

### compare
`{"type": "compare", "labels": ["Before", "After"], "items": [{"label", "before", "after", "note"}]}`.
Cards that flip between two states; a switch flips them all.

### matrix
`{"type": "matrix", "items": [{"id": "R1", "title", "likelihood": 1-5, "impact": 1-5, "owner", "text"}]}`.
A five-by-five risk grid beside a list; selecting either opens the mitigation.

### roadmap
`{"type": "roadmap", "start", "end", "today", "lanes": [...], "items": [{"lane", "title", "start", "end", "confidence", "when", "text"}]}`.
`confidence` is `committed` (solid), `likely` (hatched) or `exploring` (outlined). Bars that
overlap in a lane stack into rows.

### team
`{"type": "team", "squads": [{"name", "lead", "focus", "members": [names], "owns": [systems], "color"}]}`.
Squad cards with member initials and what each squad owns. `color` is a series or theme
color; by default squads take `s3` onward, leaving `accent` and `legacy` for status. Names
only for people who agreed to appear, or for invented demo data.

### model
`{"type": "model", "kind": "forecast" | "savings", "data": {...}, "text": "assumptions"}`.
Sliders the reader moves, a chart and a sentence that reads the result.
- `forecast` data: `remaining`, `velocity`, `growth`, `target` (date), `x`, `done`, `scope`.
- `savings` data: `now` and `after` (monthly cost), `renewal` (one-off cost), `renewal_month`,
  `plan_month`, `first`, `last` (slider range, `YYYY-MM`), `year`.

### table
`{"type": "table", "columns": [...], "rows": [[...]], "caption": "..."}`. Cells accept tokens.

### plate
`{"type": "plate", "art": key, "caption": "...", "spots": [{"anchor", "label", "title", "text"}]}`.
A painting inside a chapter. `spots` pin numbered buttons to the painting's named anchors
(see `illustration.md`); each opens a card with its title and text. Leave out `label` when
the painting already names the object. On phones, wide plates fill a taller frame and pan
as the reader scrolls.

### flow
`{"type": "flow", "labels": ["Mar 2025", "Oct 2026"], "token": "parcel", "statuses": {...}, "nodes": [{"label", "sub", "values": [then, now], "status": [then, now], "text"}]}`.
A process as a row of steps: an order's path, a request through a system, a new hire's
first week. With two or more `labels`, a switch shows every step's value and status in
each state. `statuses` maps a status name to `{"label", "color"}`. `token` sends an icon
along the steps (`parcel`, `van`, `cart`, `ball`, `rocket`...). Selecting a step opens its
`text`.

### tilemap
`{"type": "tilemap", "layout": "us-states", "frames": "@x", "values": "@by_region", "scale": {...}, "format": "pct", "markers": [...], "readout": {...}}`.
Equal squares for regions. `layout` is `us-states` or `custom` with
`"tiles": [{"id", "label", "row", "col"}]` (offices, warehouse zones, stores, countries).
`values` maps a tile id to a number or category, or to a list with one per frame.
`frames` (dates or labels) add a slider and a Play button. `scale` is
`{"kind": "sequential", "min", "max", "label"}` or
`{"kind": "category", "categories": [{"value", "label", "color"}]}`. `markers` put an icon
on a tile: `[{"tile": "NV", "label": "Reno fulfillment center", "icon": "parcel"}]`.
`readout` writes a live sentence: `{"text": "{frame}: {count} of {total} ...", "count":
{"gte": 100}}`; placeholders are `{frame}`, `{count}`, `{total}`, `{sum}`, `{mean}`,
`{max}`, `{max_label}`.

### diagram
`{"type": "diagram", "svg": "diagrams/x.svg", "alt": "...", "steps": [{"title", "text", "focus": [ids]}]}`.
A mechanism drawn as SVG in the page's own type and colors. Classes style it: `box`,
`box accent`, `box legacy`, `box soft`, `line`, `line accent`, `line dashed`, `head`
(arrowheads), `title`, `label`, `small`, `hand`, and `f-<color>`, `s-<color>`, `t-<color>`
for fills, strokes and text in any theme color. Give each part an `id`; steps dim every
part outside `focus`. `data-tip` on a part shows its text on hover or tap. Text may hold
fact tokens. Only plain shapes, text, groups, markers and gradients pass the sanitizer:
no scripts, styles, images or links out.

### quiz
`{"type": "quiz", "kicker": "Check yourself", "title", "questions": [{"q", "options": [...], "answer": index, "explain"}], "results": [{"min": 0, "label", "text"}, {"min": 1, "label"}]}`.
One question at a time; each answer shows why. `results` picks a closing line by share of
answers right (`min` from 0 to 1). For onboarding, training and guides.

### checklist
`{"type": "checklist", "title", "groups": [{"title", "items": [...]}], "key": "first-week"}`.
Tasks the reader ticks off, with a progress meter. Ticks stay in the reader's browser when
it allows storage.

### widget
`{"type": "widget", "name": "pack-drill", "script": "widgets/pack.js", "style": "widgets/pack.css", "data": {...}, "fallback": "text without scripts"}`.
A figure written for this page when no block fits. See `widgets.md`.
