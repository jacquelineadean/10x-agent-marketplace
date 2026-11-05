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
| `theme` | The page's identity: concept, palette, fonts, progress device, chapter marks, stat style, surface and words. See `identity.md`. |
| `sources` | `[{"id", "label", "detail", "as_of"}]`; every fact's `source` names one `id`. |
| `art` | Named paintings, drawn as SVG and painted by `chronicle build`. See `illustration.md`. |
| `hero` | `{"art": key, "caption": text, "stats": [stat items], "stats_title", "stats_subtitle", "stats_style"}`; title and subtitle head a receipt or ticket |
| `game` | Optional. `{}` or `{"key": "page-key", "names": {"-1": "Birdie"}}` plays every quiz as a hole; see "Games" below |
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

## Text, tokens, formats and blocks

Read `${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/blocks.md` for text tokens,
formats and every block the engine renders. chronicle adds the blocks below. An `at` is
an anchor name from the drawing or `[x, y]` in painting pixels.

### plate
`{"type": "plate", "art": key, "caption": "...", "spots": [{"anchor", "label", "title", "text"}]}`.
A painting inside a chapter. `spots` pin numbered buttons to the painting's named anchors
(see `illustration.md`); each opens a card with its title and text. Leave out `label` when
the painting already names the object. On phones, wide plates fill a taller frame and pan
as the reader scrolls.

`notes` draws pen marks over the painting, which write themselves 1.5 seconds after it
develops: `[{"at": "sign", "mark": "circle", "text": "slow down here", "pen": "red",
"dx": 80, "dy": -40}]`. Marks: `circle`, `underline`, `arrow` (from the words to the
point), `cross`, `tick`, `box`; pens: `red`, `blue`, `ink`. At most 8 notes, words under
60 characters. `dx` and `dy` place the words from the point; `size` scales the mark.

### Games
With a top-level `game`, every `quiz` is a hole. Its par is its question count plus one,
or the block's `par`; give each hole an `id`. Each pick is a stroke; a wrong pick drops
out and the reader picks again; strokes against par name the hole (Birdie, Par, Bogey;
`game.names` renames them). The page's bar gains a flag per hole, and
`{"type": "scorecard", "title": "Your card"}` totals the round. The round is kept on the
reader's device under `game.key`.

### panorama
A wide painting to drag along, with animals, places, a tide and a journal:

```json
{"type": "panorama", "id": "marsh", "art": "marsh", "title": "Walk across the island",
 "label": "Painted cross-section ...; drag it or use the arrow keys to look along it",
 "intro": "Pick an animal to open its field card.", "journal": "island-key",
 "view": {"desktop": 520, "phone": 360}, "front": ["grass"],
 "zones": [{"label": "Mudflat", "from": 1360, "to": 2360, "text": "..."}],
 "tide": {"layer": "tide", "surf": "surf", "shift": [86, -60], "start": 0.15,
          "watch": [[1360, 2360]], "notes": [{"from": 0, "text": "Low tide: ..."}]},
 "animals": [{"id": "crab", "art": "crab", "name": "Fiddler crab", "latin": "Uca pugnax",
              "where": "Mudflat", "fact": "...", "at": [1560, 900], "scale": 0.28,
              "behavior": "scuttle", "range": [1460, 1760], "tide": "low"}]}
```

`view` gives the view's height in pixels; the painting scales to it and pans sideways.
`zones` name stretches of the painting in its pixels; buttons above the view pan to them.
`front` names layers drawn in front of the animals. The `tide` slider fades the `layer`,
slides the `surf` layer by `shift` at low water, shows the last `notes` entry it has
passed, and fades animals marked `"tide": "low"` or `"high"`; on the first move it pans to
a `watch` stretch when none is in view.

Each animal names a drawing with one rig (`art`, and `rig` when the drawing has more),
stands with its foot at `at` and is drawn at `scale`. Behaviors: `wander` (walks to a
point in `range`, rests `rest` seconds, default `[2, 6]`), `scuttle` (wanders without
turning), `swim` (back and forth), `crawl` (one way, then starts again), `glide` (crosses
the sky), `arc` (leaps for 0.28 of each `period` seconds, `height` pixels high), `hop` and
`stay`. `speed` and `stride` default to the rig's, scaled. `face: -1` starts it facing
left. Animals sharing an `id` are one species. Picking one opens its card; with a
`journal` key (or `true` for one per page), every species found is kept on the device and
shared by every panorama with that key.

### rooms
Paintings with numbered details and doorways between them:

```json
{"type": "rooms", "id": "house", "title": "Through the front door", "rooms": [
  {"id": "front", "art": "house-front", "short": "Front", "kicker": "Outside",
   "title": "The front of the house", "text": "...",
   "details": [{"at": "lamp", "title": "The door lamp", "text": "..."}],
   "exits": [{"at": "door", "to": "hall", "label": "Step inside", "arrow": "up"}],
   "focus": 0.5}]}
```

Tabs list the rooms by `short`. A numbered dot opens its detail in the caption; a doorway
(`arrow`: `up`, `down`, `left`, `right`) walks to the room `to` names, pushing through the
door while the next room develops from gray. `focus` is where a phone's sideways scroll
starts, 0 to 1. Every room needs a way back.

### tour
A painted map whose stops open scenes, walked by a route in the page's bar:

```json
{"type": "tour", "id": "island-tour", "art": "map", "title": "Marrow Key",
 "hint": "Pick a stop to go there.", "key": "island-key",
 "stops": [{"id": "house", "title": "The keeper's house", "short": "Keeper's house",
            "at": "house", "chapter": "house", "intro": "...",
            "scene": {"type": "rooms", "id": "tour-house", "rooms": [ ... ]}}],
 "pins": [{"title": "The old well", "at": "well", "text": "..."}]}
```

Stops are numbered in route order; the dotted route joins them. A stop's `scene` is a
`plate`, `rooms` or `panorama` block shown in the tour's box; give a scene block its own
`id` when the same rooms or panorama also appears in a chapter. `chapter` names the
chapter that tells the stop at length. `pins` are small info dots between stops. Visits
are kept on the device under `key`.
