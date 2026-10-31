# RFC-0007 proposal map

An interactive map of [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md): the
two plugins, the shared engine, the data lanes and the ten open questions pinned to the
parts each one changes. Picks made on the published page save to the page's own store, where
Claude can read them back.

| Path | Holds |
| --- | --- |
| `animation.json` | the TAD: 12 nodes in 5 groups, 15 edges, 5 flows, 6 steps, top-down layout |
| `facts.json` | the one fact the map shows, the RFC's id |
| `page.html` | the published page: the built SVG inlined in `#map`, the step clock in `CLOCK`, the questions in `QUESTIONS` |

## Rebuild

```bash
S=plugins/chronicle/scripts/chronicle
$S animate check docs/rfc-0007-map/animation.json
$S animate build docs/rfc-0007-map/animation.json --out /tmp/rfc-0007-map --formats svg,png
```

Replace the `<svg ...>...</svg>` element inside `<div class="map" id="map">` in `page.html`
with `/tmp/rfc-0007-map/animation.svg`. Update `CLOCK` when the steps change; each step's
`start` and `end` come from chronicle's `core.motion.model.plan`. Publish `page.html` with
the Artifact tool and `capabilities: {db: {}, user: {}}`.

The page plays the TAD by setting `currentTime` on the SVG's CSS animations, so it needs no
copy of the motion code. The whole map is read 0.6 seconds before the loop ends, because
every looping track eases back to its first value in the last 0.35 seconds.
