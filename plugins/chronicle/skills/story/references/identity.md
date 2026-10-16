# A page made for its subject

A chronicle page should look like it could only be about this one subject. A page about a
hardware retailer measures reading progress with a tape measure and hangs its chapters
from aisle signs; a golf club's handbook marks chapters with flags on a course; a podcast
guide runs a clock across the top. Nothing on the page is generic decoration.

Do this design pass before writing `story.json`. It takes ten minutes and decides how
good the page can be.

## 1. Collect the subject's world

Read the brief and the facts, then list, in a scratch note:

- **Objects** people in this world handle: parcels, receipts, clipboards, tape guns; golf
  balls, scorecards, tees; whiteboards, markers, clocks; stethoscopes, charts, badges.
- **Places**: a warehouse floor, a shop counter, a fairway, an interview room, a lab bench.
- **Artifacts** that already carry numbers: a receipt, a scorecard, a boarding pass, a
  shipping label, a lab report, a scoreboard, a ticket stub.
- **Rituals and units**: a release train, a peak season, a round of eighteen holes, a
  45-minute interview, a sprint, a shift.
- **Brand**: the organization's colors, logo shapes, typefaces, tone. Use what the user
  gives you; for invented demo organizations, invent one that fits.

Pick from this list for every decision below. If a choice could appear on any page, it is
the wrong choice.

## 2. Decide the identity

Write it into `story.theme`:

```json
"theme": {
  "palette": {"paper": "#F7F2E8", "ink": "#24211E", "accent": "#2F6B4F", "legacy": "#B5652B",
              "series": ["#2F6B4F", "#B5652B", "#1F7F86", "#A7770A", "#B04F78", "#5F8A2E"],
              "colors": {"kraft": "#C49A6C", "tape": "#E2B54A", "icon": "#D9B07A"}},
  "fonts": {"display": "Fraunces", "body": "Literata", "ui": "Barlow Semi Condensed",
            "mono": "IBM Plex Mono", "hand": "Caveat"},
  "progress": {"kind": "track", "icon": "parcel", "line": "belt", "start_label": "Order placed"},
  "chapter_mark": {"style": "label", "prefix": "Parcel", "format": "padded"},
  "stats": "receipt"
}
```

### Palette

- `accent` is the new thing, the hero of the story (the new platform, the product, the
  team). `legacy` is the old thing or the risk. Charts use them as `accent` and `legacy`.
- `paper` is light and slightly tinted toward the subject (kraft, cream, cool cotton);
  `ink` is a near-black from the same family. Dark mode is derived; code checks every
  text color for contrast and darkens or lightens it until it reads.
- `series` colors group things that are not status (squads, regions, products). Keep
  `accent` and `legacy` for status only; give squads and teams their own colors.
- `colors` names extra brand colors. They become CSS variables (`--c-kraft`) and diagram
  classes (`f-kraft` fills, `s-kraft` strokes); figures accept their names as colors.
  `icon` colors the progress-bar icon and the flow token.

### Type

Pick one family per role from the list below. `chronicle check` rejects names not on it,
because a wrong weight request breaks the whole font download.

| Role | Good picks |
| --- | --- |
| display (titles) | Instrument Serif, Fraunces, Playfair Display, DM Serif Display, Gloock, Libre Caslon Display, Bodoni Moda, Young Serif, Newsreader, Big Shoulders Display, Barlow Condensed, Oswald, Bebas Neue, Anton, Space Grotesk, Outfit, Sora, Josefin Sans, Fredoka, Zilla Slab, Arvo, Roboto Slab |
| body (reading) | Source Serif 4, Literata, Newsreader, Lora, Spectral, Crimson Pro, Libre Caslon Text, Merriweather, Alegreya, Fraunces |
| ui (labels, charts) | Libre Franklin, Barlow, Barlow Semi Condensed, Schibsted Grotesk, IBM Plex Sans, IBM Plex Sans Condensed, Work Sans, Archivo, Archivo Narrow, Public Sans, DM Sans, Manrope, Rubik, Nunito, Space Grotesk |
| hand (notes on paintings) | Caveat, Shantell Sans, Kalam, Patrick Hand, Gochi Hand, Permanent Marker, Architects Daughter |
| mono (receipts, codes, timers) | IBM Plex Mono, JetBrains Mono, Space Mono, DM Mono, Courier Prime, Special Elite, VT323, Silkscreen |

The full list with weights is `assets/fonts.json` in the plugin. Pair a characterful
display face with a calm body face; let the UI face echo the subject (condensed industrial
sans for warehouses and stores, a rounded sans for consumer products, a grotesk for tech).

### The progress device

The sticky bar maps the reader's place onto an object from the subject's world.

| `kind` | Draws | Suits |
| --- | --- | --- |
| `arches` | bridge arches that fill as chapters are read | construction, migration as building |
| `track` | stops on a line with an icon riding along; `line`: `solid`, `dashed`, `belt` (conveyor), `road`, `rail`; `icon`: parcel, van, truck, cart, plane, train, ship, pin, ball, boot, rocket, dot | journeys, deliveries, pipelines, launches, roadmaps |
| `tape` | a tape measure pulled out as you read; chapter numbers on the tape | building, retail, home, anything measured |
| `flags` | a flag per chapter, filled when played, a ball rolling along | golf, sport, courses, milestones |
| `clock` | a clock face plus phase bar; chapters may carry `at` and the theme a `total` (minutes) | podcasts, talks, interviews, timed procedures, incidents |
| `steps` | numbered dots joined by a line | guides, training, onboarding, how-tos |

With `total` set (say 215 for a 3 h 35 min episode), give each chapter an `at` (the minute
it starts) and the device spaces chapters by time.

### Chapter marks

`chapter_mark.style`: `arch`, `label` (a shipping label with a barcode), `tag` (a price tag),
`sign` (a hanging aisle sign), `badge` (a stamped seal), `flag` (a pennant), `plain` (a big
numeral), `step` ("Step 1"), `none`. `prefix` adds a word ("Aisle", "Hole", "Parcel",
"Module"); `format` is `roman`, `decimal`, `padded` (01) or `alpha`.

### Number panels

`stats`: `rule` (ruled columns), `cards`, `receipt` (a till receipt with a torn foot, set in
the mono face, beside the hero text), `ticket` (a ticket stub). Give the hero
`stats_title` and `stats_subtitle` to head a receipt or ticket.

## 3. Plan the illustrations

One painting per chapter at most, plus the hero. Each one depicts a concrete thing from
that chapter's content, drawn in the subject's world, showing the real state:

- The hero states the whole story in one still life or scene. A migration three-fifths
  done shows a packing slip with three of five boxes ticked; a launch shows the product
  on launch day; a handbook shows the first-day desk.
- Each chapter's plate shows the chapter's claim: the old system as what it behaved like
  (one locked cabinet), the platform as the tools on a pegboard, the incident as the jam
  on the belt, the roadmap as a route map with the stops still to make.
- Prefer still lifes and close scenes of objects over landscapes. Objects carry labels,
  states and numbers; landscapes carry mood.
- Put live numbers on paintings with fact tokens inside SVG `<text>`: the stopwatch reads
  `{{experience.p95_now}}`, the packing slip `{{migration.payments_dual_run|int}}`.
- Mark hotspots with `data-anchor` and add `plate` spots for what a reader should learn
  from each object. Keep spot labels short or leave them out when the painting already
  labels the thing.

`references/illustration.md` explains how to draw these as SVG for the painter.

## 4. Choose figures that fit the material

Prefer the figure a person from this world would draw on a whiteboard:

| Material | Figure |
| --- | --- |
| A process, a journey, a pipeline, a request path | `flow` (with two states to compare), or `diagram` for branches |
| Places, regions, stores, offices, rollouts by region | `tilemap` with frames and a play button |
| A mechanism (how something broke, how a system works) | `diagram` with steps |
| Knowledge a reader should keep (training, onboarding, guides) | `quiz`, `checklist` |
| A what-if the reader should feel | `model` sliders |
| Something no block does (a calibration drill, a drag-to-order game, a simulator) | `widget` (see `references/widgets.md`) |

## Worked identities

| Page | Palette and type | Device and marks | Paintings |
| --- | --- | --- | --- |
| Order-platform migration (Keystone example) | forest green and rust on kraft paper; Fraunces, Literata, Barlow Semi Condensed, Plex Mono | parcel on a conveyor belt; parcel labels; receipt stats | packing table, filing cabinet, pegboard, jammed conveyor, shop counter, crew vests, route map |
| Retail history from a podcast | apron orange and blueprint blue on warm paper; Libre Caslon, Barlow Condensed | tape measure across the episode time; aisle signs | store at dawn, paint-can stack, apron on pegboard, flatbed truck |
| Golf company handbook | fairway green, flag red, bunker sand; Instrument Serif, Libre Franklin | nine flags; hole numbers; scorecard quiz panels | tee box, launch monitor bay, putting green, clubhouse |
| System design interview guide | marker blue, green and red on cool paper; Gloock, Literata, Schibsted Grotesk, Shantell Sans | 45-minute interview clock; painted numerals | whiteboard room, index cards, failing node diagram |
| Product launch recap | the product's brand colors; a rounded sans | rocket on a dashed track; step marks | the product in use, launch-day desk, the support inbox |
| Incident review | alarm red as legacy, calm blue as accent; a grotesk and a mono | incident clock with `at` minutes; badges | the failing component as an object, the pager, the fix |
