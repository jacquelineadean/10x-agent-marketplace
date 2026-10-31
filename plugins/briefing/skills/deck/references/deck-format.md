# The deck file

A deck is a story file with `"layout": "deck"`. Read
`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/blocks.md` for tokens, formats and the
blocks every layout shares, and `${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/facts.md`
for the facts file.

```json
{
  "schema_version": 1,
  "layout": "deck",
  "meta": {"title": "...", "kicker": "...", "dek": "...", "byline": ["..."]},
  "theme": {"concept": "..."},
  "sources": [{"id": "github", "label": "GitHub", "detail": "...", "as_of": "2026-10-14"}],
  "chapters": [
    {"id": "decision", "kicker": "The decision", "title": "...", "dek": "...", "columns": 2,
     "notes": "What to say.", "blocks": [ ... ]}
  ]
}
```

| Key | Meaning |
| --- | --- |
| `meta` | The cover slide: kicker, title, dek, byline. |
| `chapters[]` | One slide each, in order. `title` states the slide's point as a sentence. |
| `columns` | 1 (default), 2 or 3: how the slide's blocks sit side by side. |
| `notes` | Speaker notes, shown with the Notes button and never on the slide. |
| `sources` | The last slide, and the label each number's hover shows. |
| `"build": true` on a block | The block appears on a later click, in block order. |

## Blocks for decks
Use `kpi`, `chart`, `table`, `stats`, `compare`, `timeline`, `roadmap`, `stepper`, `flow`,
`diagram`, `prose` and `animation`. A scrolly block needs a scrolling page; use a stepper.

### kpi
`{"type": "kpi", "items": [{"label", "value": "@path", "target": number or "@path", "better": "up" | "down", "warn": 10, "change": "@path", "spark": "@series", "format", "note"}]}`.
Tiles with value, target, status and sparkline. Status is set in code: on target when the
value is on the `better` side of the target, near target within `warn` percent (10 by
default), off target beyond. Every value needs a target and a query in `queries.json`.

### animation
`{"type": "animation", "svg": "build/anim/animation.svg", "alt": "...", "caption", "source"}`.
An animation built with `animate build ... --formats svg` (a blueprint TAD, a diagram).
Its first step plays when the slide opens; each click plays the next step, then the deck
moves on.

## Fit
A slide holds about 60 words and 4 blocks; `check` warns past either. A title over 80
characters wraps badly. Put detail in `notes`, not on the slide.
