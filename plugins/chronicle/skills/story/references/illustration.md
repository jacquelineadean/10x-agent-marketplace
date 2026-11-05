# Paintings

Every plate is painted by code. You draw the picture as plain SVG; `chronicle build`
paints it in ink and watercolor: each filled shape becomes a transparent wash that lands a
little loose of its outline, darkens at the rim, settles into the paper grain and grades
toward the shadow side; each stroke becomes a dip-pen line that wavers and overshoots its
corners. Text in the drawing stays live text in the page's fonts. A painting takes one to
three seconds and is repainted only when its drawing or the painting code changes.

Decide what to paint with `references/identity.md` first: a concrete object or scene from
the subject's world, showing the real state.

## The scene entry

```json
"art": {
  "hero": {"svg": "art/hero.svg", "seed": 7, "vignette": "soft",
           "alt": "Watercolor of a packing table: an open parcel ..."},
  "stamp": {"svg": "art/lesson-stamp.svg", "width": 600, "vignette": "spot", "alt": ""}
}
```

| Key | Meaning |
| --- | --- |
| `svg` | The drawing file, relative to `story.json` (keep drawings in `art/` in the run folder), or the SVG text itself |
| `width` | Painted width in pixels. Default: the viewBox width, or 1600 when the viewBox is narrower than 1000 |
| `seed` | Changes the brush randomness; try another seed if a wash lands badly |
| `vignette` | `soft` (default for drawings), `deckle` (torn paper edge), `spot` (an oval fading into the page, for small vignettes), `none` |
| `style` | Scene-wide brush settings: `light` (degrees the light comes from, default 225: upper left), `shade`, `loose`, `wet`, `edge`, `grain`, `flow`, `opacity`, `line`, `jitter`, `blooms` |
| `alt` | What the painting shows, for screen readers. Write it; describe the objects and their state |

## Drawing for the painter

Sizes: `viewBox="0 0 1600 900"` for the hero, 1600 by 600 to 900 for chapter plates, and
`0 0 600 600` with `"width": 600` and `"vignette": "spot"` for lesson vignettes.

Allowed: `path`, `rect`, `circle`, `ellipse`, `line`, `polyline`, `polygon`, `g`, `use`
(pointing at an id in the same file), `defs`, `symbol`, `linearGradient`, `text`, and
`transform` anywhere. Anything else is an error that names the element.

**Order is depth.** Shapes paint in document order and a filled shape covers what is under
it, as in any SVG. Draw back to front: wall, floor or table, far objects, cast shadows,
near objects, details on them, then overlay text.

**Transparent things.** `fill-opacity` below 1 or `data-paint="glaze"` glazes over what is
below instead of covering it: glass, cast shadows, light beams, tape, water.

**Composition.**
- One subject, large, slightly off center, overlapping a second and a third object. Overlap
  makes depth; a row of separate objects looks like clip art.
- A table edge, floor line or horizon at 55 to 70 percent of the height gives the objects
  something to stand on. Cast a glazed shadow under each standing object.
- Keep 60 pixels clear at the edges; the soft vignette fades them.
- Nothing important smaller than 14 pixels at 1600 wide: on a phone the painting shows at
  a quarter of that, and on phones wide plates pan sideways at roughly half size.
- Leave clear space where hotspot dots and their labels will sit.

**Boxes and furniture in perspective.** Draw the front face as a rectangle, then the top
and the right side as parallelograms offset by one depth vector, such as `(140, -60)`.
Open flaps are parallelograms hinged on an edge. This simple oblique view reads well in
watercolor and is easy to get right.

**Lines.** Contours 2.2 to 2.8 wide, inner details 1.4 to 2, in a warm near-black such as
`#2b231d`; colored ink (`stroke="#2f6b4f"`) for check marks, routes and writing.
`data-line="pencil"` draws a light graphite line for wood grain, paper rules, construction
lines and things not yet built. `data-line="lift"` scrubs a highlight back to the paper:
the glint on glass, chrome or a reflective stripe.

**Color.** Watercolor colors are a little muted: pick them as a painter mixes them, not as
a UI swatch. Use the brand colors on the objects that matter and four or five supporting
hues. Fill names may be pigments: `ultramarine`, `cobalt`, `cerulean`, `prussian`,
`indigo`, `paynes-grey`, `neutral-tint`, `lavender`, `cobalt-teal`, `viridian`,
`sap-green`, `hookers-green`, `olive`, `lemon`, `gamboge`, `yellow-ochre`, `raw-sienna`,
`burnt-sienna`, `burnt-umber`, `sepia`, `vermilion`, `cadmium-orange`, `rose`, `madder`,
`warm-grey`, `ink`, `graphite`.

**Brush hints** (on any shape or group; groups pass them down):

| Attribute | Effect |
| --- | --- |
| `data-paint` | `wash` (default), `glaze` (transparent), `wet` (soft wet-in-wet edges, for walls, skies, shadows), `dry` (dry brush streaks), `reserve` (back to bare paper), `none` (stroke only) |
| `data-shade` | 0 to 1: how much darker the side away from the light gets. 0.3 to 0.6 for solid objects, 0 for flat paper and walls |
| `data-wet`, `data-edge`, `data-grain`, `data-blooms` | wash softness, rim darkening, granulation, backruns |
| `data-loose` | how far the wash lands off its outline; 0 for exact fills such as dot grids |
| `data-hatch` | 0 to 1: pen hatching across the shape, for shade without a darker wash |
| `data-line` | `ink` (default), `pencil`, `lift`, `none` |
| `data-overshoot` | 0 stops lines running past their corners |

A `linearGradient` fill (default bounding-box units) paints as a wet-in-wet blend from
color to color.

## Text on paintings

`<text>` never gets painted: it becomes live text over the painting, so it stays sharp,
translates and can hold facts.

- `data-label`: `hand` (default; the theme's handwriting face), `label` (small caps UI, for
  printed labels and signs), `caption`, `display`, `mono` (codes, tickets), `number`.
- Fact tokens work: `<text>{{experience.p95_now}}</text>`. Numbers typed into drawing text
  get the same "no fact token" warning as prose.
- Size 16 to 34 at 1600 wide; rotate with `transform="rotate(-6 x y)"` to sit on a tag.
- `fill` sets the color; `text-anchor` works.

## Hotspots

Put an anchor where a plate spot's numbered dot should sit:
`<circle cx="866" cy="236" r="1" fill="none" stroke="none" data-anchor="cabinet"/>`. Place
it in clear space beside the object, because the dot and its label cover what is under
them. In the story, `{"type": "plate", "art": "monolith", "spots": [{"anchor": "cabinet",
"label": "One codebase", "title": "...", "text": "..."}]}`. Leave out `label` when the
painting already names the object; the dot then shows only its number.

## Moving parts

Wrap a part in `<g data-layer="name" data-motion="..." data-travel="40">`. It is painted on
its own sheet and moved by the page.

| Motion | Movement | Use for |
| --- | --- | --- |
| `drift` | a slow wander | steam, birds, smoke, paper |
| `descend`, `rise` | moves down or up by `travel` as the reader scrolls past | a part settling into place, a lid, a crane load |
| `cross` | slides right by `travel` in a loop, fading at the ends | parcels on a belt, traffic |
| `fall` | falls in a loop | rain, snow |
| `sway`, `bob` | rocks on its base, floats up and down | hanging signs, tags, toys |
| `spin` | turns around its own center | a beacon, a fan, a wheel |
| `pop` | appears once with a small bounce when the painting comes into view | a stamp, a check mark |

Moving solid objects get transparency from their paint, so they cover what they pass.
Keep moving parts few (one or two a painting) and small.

## Rigs: animals and machines in parts

A rig is a figure drawn in parts that turn about their joints: a hog whose legs swing and
whose head drops to root, a crab waving its claw, a gull's wings. Wrap the figure in
`<g data-rig="hog" data-gait="root">` and each part in
`<g data-part="leg-fore-near" data-pivot="410 230">`. Each part is painted on its own
sheet, opaque, and turns about its pivot (in the part's own coordinates) by a rule for
its role. `examples/field-guide/art/hog.svg` is a complete rig.

Draw rigs facing right. Parts paint in document order, so draw the far legs, the near
legs, the tail and the head, then the body on top: the body hides the joints.

| Role | Moves | Numbers (defaults) |
| --- | --- | --- |
| `leg`, `flipper` | swings while the figure moves, one cycle a stride | `data-amp` 18 degrees (22 for flippers); `data-phase` in cycles, 0 and 0.5 for opposite legs |
| `head` | nods twice a stride, drops by `down` at rest, looks about slowly | `data-down` 0, `data-nod` 3, `data-look` 2 |
| `tail`, `wing` | swings all the time | `data-amp` 10 (wings 6), `data-speed` 3 (wings 1.4) radians a second |
| `ear` | flicks about every seven seconds | `data-amp` -30, `data-speed` 0.9 |
| `claw` | waves at rest | `data-amp` -24, `data-speed` 5 |
| `static` | never turns | none |

The role comes from `data-role`, else from the part's name: `leg-*`, `fl-*` and `rl-*`
(front and rear limbs), `flipper-*`, `head`, `tail`, `ear-*`, `wing-*` and `claw`; any
other name is static. Positive angles turn clockwise, so a positive `down` lowers a
right-facing snout.

The gait says what the rig does where it stands, on a plate and in a `rig` animation:

| `data-gait` | Plays |
| --- | --- |
| `still` (default) | tails, wings, ears and claws only |
| `walk`, `swim` | legs or flippers stride, the head nods, the body bobs by `data-bob` (default 2) |
| `crawl` | flippers stroke on time, 0.45 seconds a stroke |
| `graze`, `root` | the head drops by `down` and dips slowly; the legs rest |

`data-foot="x y"` marks where the figure stands (default: the bottom middle of its
parts); a panorama places an animal by this point and mirrors it about it. `data-stride`
(pixels a leg cycle, default 60) and `data-speed` (pixels a second, default 30) set how a
walking figure moves; a panorama scales both with the animal.

An animal for a panorama is drawn alone in its own file, one rig a file, painted small:
`"hog": {"svg": "art/hog.svg", "width": 600, "seed": 11, "alt": ""}`.

## Panoramas and tour maps

A `panorama` painting is wide (3200 by 1000 for a walk across a place) and holds no rigs:
its animals come from their own drawings. Name its layers for the block: one the tide
fills (a wash over the flats), one the surf slides up the beach, and a strip of grass or
reeds the block draws in front of the animals. Leave out their `data-motion`; the
panorama moves them. Leave the bottom fifth clear enough for animals to stand on.

A `tour` map marks each stop and pin with a `data-anchor` and leaves room beside each for a
numbered badge and its label. Rooms for a `rooms` block mark each detail and doorway with
an anchor too.

## Repeated details

Generate repeats with a short script rather than by hand: pegboard holes, barcode bars,
bricks, seats, tiles. One `path` with many small subpaths paints in one pass and much
faster than hundreds of separate shapes.

## Check the painting

After `chronicle build`, open `build/art/<key>.webp` and look at it, then look at it again
on the built page at phone width. Fix:
- Objects that do not read at a glance: add the one detail that names them (a slot and a
  torn edge make a receipt printer; a core and a grip make a tape gun).
- Clip-art flatness: add overlap, a cast shadow and `data-shade`.
- Collisions between labels, hotspot dots and painted detail: move the anchor or the text.
- Empty corners or a crowded center: move objects, or change `seed`.

## Landscape presets and motifs

The older landscape scenes still work for pages that want scenery or a mood more than
objects. They take `{"preset": NAME, "params": {...}}` or an `elements` list of motifs;
`chronicle motifs` prints them all with their parameters.

| Preset | Params | Moving layers and anchors |
| --- | --- | --- |
| `bridge-hero` | `arches`, `built`, `mood` | keystone descends on scroll; anchors `hook`, `load`, `slot` |
| `bridge-old-crossing`, `bridge-piers`, `bridge-flood`, `bridge-span` | `arches`, `built` | rain, traffic; anchors `patch`, `queue`, `center`, `centering` |
| `road-ahead` | `milestones`, `mood` | anchors `m1` to `mN` |
| `valley` | `mood` (`day`, `dawn`, `dusk`, `storm`, `mist`), `clouds` | birds drift |
| `waterfront` | `mood`, `towers` | none |
| `keystone-spot` | none | a small vignette for `lesson` blocks |

Motifs: `sky`, `sun`, `mountains`, `hills`, `treeline`, `tree`, `grass`, `bank`, `water`,
`rain`, `birds`, `arch_bridge`, `trestle`, `crane`, `road`, `milestone`, `buildings`,
`vehicle`, `figure`, and the brush primitives `wash`, `ink`, `pencil`, `glow`, `reserve`,
`drybrush`, `splatter`, `reflect`.
