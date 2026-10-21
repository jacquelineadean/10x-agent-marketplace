# The animation file

`animation.json` holds one animation. The keys every kind shares are below; the kind's
own object (`tad`, `diagram` or `scene`) is in `tad.md` and `diagram-and-scene.md`.

```json
{
  "schema_version": 1,
  "kind": "tad",
  "facts_file": "facts.json",
  "meta": {
    "title": "How an order moves through Checkout",
    "kicker": "Architecture walkthrough",
    "description": "One sentence on what the animation shows; it is the alt text.",
    "credit": "Platform team",
    "sources": [{"label": "Checkout design doc", "detail": "rev 7, Oct 2026"}]
  },
  "theme": {"concept": "...", "palette": {...}, "fonts": {...}},
  "frame": {"size": "16:9"},
  "timing": {"pace": 1.0},
  "tad": {...},
  "steps": [{"caption": "...", "show": [...], "flow": [...]}]
}
```

## meta

| Key | Meaning |
| --- | --- |
| `title` | Required. Shown top left and as the SVG's `<title>`. |
| `description` | Required. One sentence on what the animation shows. It becomes the SVG's `<desc>` with the step captions, the caption under the HTML figure and the alt text. |
| `kicker` | A short line above the title. |
| `credit` | Shown top right: the team, or "Example data". |
| `sources` | `[{label, detail, url}]`, listed in the description and under the HTML figure. |

All text may hold fact tokens. A bare number in text gets a warning, as in a story.

## theme

The story theme's `concept`, `palette`, `dark` and `fonts` (see the story skill's
`references/identity.md`). Write the concept first. The theme is scoped to the
animation's own class, so two animations, or an animation inside a story page, never
change each other's colors. Fonts load from Google Fonts where the file is shown inline
or opened directly; see `formats.md` for an SVG shown as an image.

## frame

| Key | Values | Default |
| --- | --- | --- |
| `size` | `16:9` 1280 x 720, `4:3` 1024 x 768, `1:1` 1080 x 1080, `4:5` 1080 x 1350, `9:16` 1080 x 1920, `wide` 1600 x 700 | `16:9` |
| `width`, `height` | whole pixels from 320 to 3840, in place of `size` | |
| `title` | false hides the kicker, title and credit (for a slide that has its own) | true |
| `captions` | false hides the caption band | true |
| `progress` | false hides the step strip | true with 2 or more steps |
| `background` | `paper`, `surface`, `none` (transparent, for slides) | `paper` |
| `theme` | `auto` follows the viewer's color scheme where the browser passes it in; `light` or `dark` fixes it | `auto` |

Type sizes scale with the frame: 1 at 1280 x 720, larger for bigger and taller frames.

## timing

| Key | Meaning | Default |
| --- | --- | --- |
| `pace` | multiplies every step's time; 1.3 for a slower read | 1.0 |
| `lead` | seconds before the first step | 0.6 |
| `hold` | seconds the last step stays before the loop restarts | 2.0 |
| `loop` | false plays once and stops on the last frame | true |
| `duration` | seconds, only for an animation with no steps | 8 |

A step lasts the longest of: 2.2 seconds, its caption's reading time (about 190 words a
minute after a 1-second settle) and what it plays (a flow's packets need about 0.75
seconds a hop). A step's own `duration` (0.5 to 60 seconds) overrides all three; the
longest step code picks is 12 seconds.

## steps

```json
{"caption": "The order service saves each order, then asks Payments to charge the card.",
 "show": ["core", "cards"], "flow": ["place"]}
```

| Action | Does | tad | diagram | scene |
| --- | --- | --- | --- | --- |
| `caption` | one sentence shown under the figure while the step plays | yes | yes | yes |
| `show` | parts appear, one after another | parts, groups, flows | ids | spots, layers |
| `hide` | parts fade out | yes | yes | yes |
| `draw` | lines stroke themselves on, from start to end | as `show` | ids | |
| `flow` | a packet runs along each path in order | flows, edges | path, line or polyline ids | |
| `focus` | everything else dims (a scene darkens around the spots) | yes | yes | yes |
| `pulse` | the parts swell twice to catch the eye | yes | yes | spots |
| `state` | `{id: state}` marks a part as new, failing or planned | yes | | |

A part named in `show` or `draw` starts hidden and appears in that step; a part never
named in either is on screen from the start. States stay until a later step sets
`normal`. Focus lasts one step.

Write one idea per step. Show the parts a flow needs in the same step or an earlier one.
End on the step that lands the point, and let `hold` keep it on screen.

## What code does

- Places each step on one clock and draws every motion as a CSS keyframe track that
  spans the whole loop. The rest value of every track is the final picture, so a still
  copy (reduced motion, a slide editor, a print) shows everything.
- Pauses for people who prefer reduced motion: the SVG then shows the still.
- Writes the step captions into the SVG's description for screen readers.
