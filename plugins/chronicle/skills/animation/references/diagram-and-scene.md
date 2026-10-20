# Drawn diagrams and painted scenes

## Diagrams (`kind: "diagram"`)

```json
"diagram": {"svg": "drawing.svg"}
```

`svg` is a file beside `animation.json` or inline `<svg>` markup. The drawing is the story
diagram format: the classes `box`, `box accent`, `box legacy`, `box soft`, `line`,
`line accent`, `line legacy`, `line dashed`, `head`, `title`, `label`, `small`, `hand`,
and `f-<color>`, `s-<color>` for theme fills and strokes (see the story skill's
`references/story-format.md`). The same sanitizer runs: plain shapes, text, groups,
markers and gradients only; no scripts, styles, images or links out. Text may hold fact
tokens. A diagram from a story page plays as it is.

Steps name element ids:

| Action | Rule |
| --- | --- |
| `show`, `hide` | any element with an id: a `<g>` around a box and its text shows them together |
| `draw` | every solid stroke inside the part strokes itself on; dashed lines fade in instead |
| `flow` | a `path`, `line` or `polyline`, drawn from where the packet starts to where it ends |
| `focus` | every other part with an id dims; the parts inside a focused group stay lit |
| `pulse` | the part swells twice |

Ids inside `<text>`, `<defs>` or a `<marker>` cannot be named. Give a packet's path an
id of its own even when it sits inside a group: `<path id="p1" class="line" .../>`.

Draw for the frame: a viewBox about as wide as the frame's stage (980 x 330 fills a
16:9 frame under a title and captions). Code centers and scales the drawing, up to 1.6
times for a small drawing.

## Scenes (`kind: "scene"`)

```json
"scene": {
  "art": {"svg": "art/jam.svg", "seed": 3, "vignette": "soft"},
  "develop": true,
  "spots": [{"id": "clock", "anchor": "clock", "label": "The pool runs dry"}]
}
```

- `art` is an art spec exactly as in a story (`svg`, `preset` or motif `elements`, with
  `seed`, `vignette`, `width`). Draw it with the story skill's `references/illustration.md`.
  `build` paints it once into `build/art/` and repaints only when the drawing changes.
- Layers the drawing marks with `data-layer` keep their story motion (`sway`, `bob`,
  `drift`, `spin`, `fall`, `cross`, `rise`, `descend`, `pop`) on the animation's loop.
- `develop` (default true) washes the painting from a gray sketch into color over the
  first 3 seconds.
- `spots` are numbered dots with a label at a `data-anchor` point of the drawing. A spot
  named in a step's `show` appears in that step; one never named is up from the start.
- Steps name spot ids and layer names. `focus` darkens the painting outside the named
  spots and layers; `pulse` swells a spot.

A story's plate becomes a scene by pointing `art.svg` at the story's drawing and
`facts_file` at its facts, as `examples/animation-scene/` does with Keystone.
