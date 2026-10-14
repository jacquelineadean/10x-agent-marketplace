# Paintings

Every plate is painted by code from a scene in `story.art`. A painting takes 2 to 4
seconds and is cached; it is repainted only when its scene or the painting code changes.

## Choose a metaphor first

One visual metaphor carries the whole page, and each plate shows a stage of it. Pick the
one whose stages match the story's stages, and paint the real state (three of five
arches built means `"built": 3.0`).

| Story | Metaphor | Presets |
| --- | --- | --- |
| Migration, replacement, rebuild | A new stone bridge beside an old trestle | `bridge-hero`, `bridge-old-crossing`, `bridge-piers`, `bridge-flood`, `bridge-span` |
| Roadmap, plan, next steps | A road toward mountains with marker flags | `road-ahead` (anchors `m1`... for spots) |
| Steady operations, a calm quarter | A river valley in some weather | `valley` with `mood` |
| Growth, a platform or city of services | A waterfront skyline at dusk | `waterfront` |
| A lesson or a principle | A small vignette | `keystone-spot` |

## Presets

```json
"art": {
  "hero": {"preset": "bridge-hero", "params": {"arches": 5, "built": 3.75, "mood": "dawn"},
           "alt": "Watercolor of ..."}
}
```

| Preset | Params | Moving layers and anchors |
| --- | --- | --- |
| `bridge-hero` | `arches`, `built` (finished arches; a fraction waits for its keystone), `mood` | keystone descends into its slot as the reader scrolls; birds drift; anchors `hook`, `load`, `slot` |
| `bridge-old-crossing` | none | anchors `patch`, `queue` |
| `bridge-piers` | `arches` | anchor `center` |
| `bridge-flood` | `arches`, `built` | rain falls; anchor `centering` |
| `bridge-span` | `arches`, `built` | traffic crosses the deck |
| `road-ahead` | `milestones` (number of flags), `mood` | anchors `m1` (nearest) to `mN`; birds drift |
| `valley` | `mood` (`day`, `dawn`, `dusk`, `storm`, `mist`), `clouds`, `width`, `height` | birds drift |
| `waterfront` | `mood`, `towers`, `width`, `height` | none |
| `keystone-spot` | none | none; for `lesson` blocks |

Every preset also takes `seed`; change it for a different arrangement of the same scene.
`alt` describes the painting for screen readers. Write it.

## New scenes from motifs

When no preset fits, compose one. Coordinates are scene pixels, origin top left. Paint far
to near: sky, mountains, hills, water, structures, then foreground banks and trees.

```json
"art": {
  "harbor": {
    "size": [1600, 700], "seed": 5, "vignette": "deckle",
    "elements": [
      {"motif": "sky", "horizon": 430, "mood": "dawn", "clouds": 3},
      {"motif": "mountains", "base": 440, "height": 140},
      {"motif": "water", "shape": [[-20, 450], [1620, 450], [1620, 720], [-20, 720]]},
      {"motif": "buildings", "x0": 900, "x1": 1500, "base": 452, "tallest": 220, "count": 7},
      {"motif": "reflect", "waterline": 452, "depth": 200, "strength": 0.7},
      {"motif": "bank", "outline": [[-30, 420], [260, 470], [320, 720], [-30, 720]]},
      {"motif": "tree", "x": 120, "ground": 520, "height": 220}
    ],
    "layers": [
      {"name": "birds", "motion": "drift", "travel": 40,
       "elements": [{"motif": "birds", "x": 600, "y": 160, "count": 5}]}
    ],
    "anchors": {"pier": [1100, 440]}
  }
}
```

- `vignette`: `deckle` (torn paper edge, default), `soft`, `spot` (an oval fading into the
  page, for small vignettes) or `none`.
- `layers` are painted separately and moved by the page. `motion`: `descend` (moves down
  by `travel` as the reader scrolls), `drift`, `fall` (rain), `cross` (moves right by `travel`),
  `none`.
- `anchors` name points that `plate` spots can pin to.
- `chronicle motifs` prints every motif with its parameters. The main ones: `sky`, `sun`,
  `mountains`, `hills`, `treeline`, `tree`, `grass`, `bank`, `water`, `rain`, `birds`,
  `arch_bridge`, `trestle`, `crane`, `road`, `milestone`, `buildings`, `vehicle`, `figure`.
- Brush primitives draw anything else: `wash` (a filled shape: `shapes` is a list of
  point lists, with `pigment`, `opacity`, `wet`, `edge`, `blooms`, `gradient`, `occlude`),
  `ink` (a pen line through `points`), `pencil`, `glow`, `reserve` (back to bare paper),
  `drybrush`, `splatter`, `reflect`.

Pigments: `ultramarine`, `cobalt`, `cerulean`, `prussian`, `indigo`, `paynes-grey`,
`neutral-tint`, `lavender`, `cobalt-teal`, `viridian`, `sap-green`, `hookers-green`, `olive`,
`lemon`, `gamboge`, `yellow-ochre`, `raw-sienna`, `burnt-sienna`, `burnt-umber`, `sepia`,
`vermilion`, `cadmium-orange`, `rose`, `madder`, `warm-grey`, `ink`, `graphite`, or any
`#rrggbb`. Keep a scene to five or six pigments.

## Check the painting

After `chronicle build`, open `build/art/<key>.webp` and look at it. Fix overlaps and empty
corners by moving elements or changing `seed`, then rebuild.
