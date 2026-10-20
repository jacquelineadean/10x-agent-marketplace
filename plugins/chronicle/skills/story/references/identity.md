# A page made for its subject

A chronicle page should look like it could only be about this one subject. A page about a
hardware retailer measures reading progress with a tape measure and hangs its chapters
from aisle signs; a golf club's handbook marks chapters with flags on a course; a podcast
guide runs a clock across the top. Nothing on the page is generic decoration.

Do this design pass before writing `story.json`. It takes ten minutes and decides how
good the page can be. Start every page from `chronicle new`, never from an example's
`story.json`: a copied theme carries the example's look into a page about something else.

## 0. Find the concept

The concept is one sentence naming the world the page borrows its look and its
interactions from. Take it from the inputs in this order, and stop at the first that
gives one:

1. **What the user supplied**: brand colors, a logo, typefaces, screenshots, a page they
   liked, files whose own design shows the house style. These win over any idea of yours.
2. **The words of the request**: the format noun sets the structure. "Field guide" means
   specimen entries and a trail map; "employee handbook" for a golf simulator means a
   yardage book with a hole per chapter; "episode visualization" means the episode's own
   clock; "postmortem" means a timeline read minute by minute.
3. **The material's world**: the objects, places and rituals the content is about (step 1).
4. **The point of the page**, as a picture: a migration as a parcel moving through a
   warehouse, a turnaround as a tide going out and coming back.

Write the sentence into `theme.concept`, with where it came from: "A yardage book for a
golf-simulator club, from the request's 'handbook' and the club's own scorecards". Every
choice below must follow from it. `chronicle check` warns when it is empty.

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
  "concept": "An order platform told through its own warehouse, from the material",
  "palette": {"paper": "#F7F2E8", "ink": "#24211E", "accent": "#2F6B4F", "legacy": "#B5652B",
              "series": ["#2F6B4F", "#B5652B", "#1F7F86", "#A7770A", "#B04F78", "#5F8A2E"],
              "colors": {"kraft": "#C49A6C", "tape": "#E2B54A", "icon": "#D9B07A"}},
  "fonts": {"display": "Fraunces", "body": "Literata", "ui": "Barlow Semi Condensed",
            "mono": "IBM Plex Mono", "hand": "Caveat"},
  "progress": {"kind": "track", "icon": "parcel", "line": "belt", "start_label": "Order placed"},
  "chapter_mark": {"style": "label", "prefix": "Parcel", "format": "padded"},
  "stats": "receipt",
  "surface": {"texture": "plain", "corners": "soft", "frame": "none"},
  "words": {"sources": "Shipping manifest", "show_numbers": "Open the slip"}
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
| `route` | an icon walking a path you draw: `path` is SVG path data in a 1000 x 40 box, left to right; stops fall at equal distances along it | trails, rivers, coastlines, subway and race routes, a vine, a cable |
| `steps` | numbered dots joined by a line | guides, training, onboarding, how-tos |

`icon_path` replaces the icon on `track` and `route` with your own drawing: SVG path data
centered on 0,0 within about 10 units, filled with the `icon` color. Draw the subject's own
token: a loggerhead for a sea-turtle guide, a microphone for a podcast, a golf cart.

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

### Surface

`surface` sets the page's material:

| Key | Values | Use |
| --- | --- | --- |
| `texture` | `plain`, `ruled` (a logbook or notebook), `grid` (graph paper, a blueprint), `dots` (a dot-grid journal) | the paper the subject writes on |
| `corners` | `square`, `soft`, `round` | square for print and engineering, round for consumer products |
| `frame` | `none`, `mat` (a print on a white mat), `tape` (pinned into a field notebook or scrapbook) | how paintings hang |

### Words

`words` renames the page's controls and headings, so the page speaks its world's language.
Keys: `sources`, `source`, `show_numbers`, `hide_numbers`, `step`, `of`, `back`, `next`,
`play`, `pause`, `question`, `next_question`, `see_score`, `score`, `try_again`, `done`,
`overview`. A golf handbook sets `question` to "Hole" and `see_score` to "Card your score";
a field guide sets `sources` to "Field notes"; a coffee handbook sets `question` to "Cup".
Quiz `results` labels follow the same world: "Birdie", "Par", "Bogey".

### The signature figure

Each page has one figure only it would have, the thing a reader remembers. Find it by
asking what a person in this world does with their hands, then build it from a block with
the theme's words, or a widget when no block fits:

| Page | Signature figure |
| --- | --- |
| Golf-simulator handbook | each chapter's quiz played as a hole, scored birdie to bogey; a launch-monitor calibration drill |
| System design podcast guide | a whiteboard diagram the reader pokes with a red pen to see what each box costs |
| Island field guide | a painted map toured stop by stop, habitat zones that switch the species shown |
| Order-platform migration | the payments rollout played state by state; an order's path compared then and now |

### Check that the page is its own

`chronicle check` compares the theme with the bundled examples and with sibling run
folders. It warns when two of type, accent, paper, progress device, chapter mark and stat
panel are chronicle's defaults, and when three or more match another page. Change the
theme until the warning goes, starting from the concept. A brand that fixes the palette
leaves the device, marks, surface and words to make the page its own.

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
| Golf-simulator club handbook (a yardage book) | fairway green, flag red, bunker sand; Instrument Serif, Libre Franklin | nine flags; "Hole" marks; quiz words "Hole", "Card your score"; scorecard quiz panels | tee box, launch monitor bay, putting green, clubhouse |
| System design podcast guide | marker blue, green and red on cool paper; Gloock, Literata, Schibsted Grotesk, Shantell Sans for marker notes | 45-minute interview clock with phases; painted numerals; `grid` texture | whiteboard room, index cards, failing node diagram, red-pen notes on paintings |
| Island field guide | live-oak green, stucco red, tabby, marsh gold, sound blue on cream; Young Serif, Spectral, Archivo Narrow, Caveat, Courier Prime | a boot walking the island road (now a `route` drawn as the real road); a painted map toured stop by stop; `tape` frames suit it | the naturalist's desk, the island map, the tabby house, a nest at night |
| Support desk review (Lantern Bay example) | lamp amber and storm blue on log paper; Libre Caslon, IBM Plex Sans Condensed, Courier Prime | `route` along a coastline with a lighthouse `icon_path`; "Watch" badges; ticket-stub stats; `ruled` texture, `tape` frames | the harbor at dawn |
| Product launch recap | the product's brand colors; a rounded sans | rocket on a dashed track; step marks | the product in use, launch-day desk, the support inbox |
| Incident review | alarm red as legacy, calm blue as accent; a grotesk and a mono | incident clock with `at` minutes; badges | the failing component as an object, the pager, the fix |
