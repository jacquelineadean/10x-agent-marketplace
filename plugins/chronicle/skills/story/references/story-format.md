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
formats and every block the engine renders. chronicle adds one block:

### plate
`{"type": "plate", "art": key, "caption": "...", "spots": [{"anchor", "label", "title", "text"}]}`.
A painting inside a chapter. `spots` pin numbered buttons to the painting's named anchors
(see `illustration.md`); each opens a card with its title and text. Leave out `label` when
the painting already names the object. On phones, wide plates fill a taller frame and pan
as the reader scrolls.
