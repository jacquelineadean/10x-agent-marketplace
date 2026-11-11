# Technical architecture diagrams (`kind: "tad"`)

A TAD is data: what the system is made of, how the parts talk, and the paths to watch.
Code places every part, routes every line around the boxes, draws icons, and plays the
steps. Claude never gives coordinates unless a layout needs a nudge (`tier`, `lane`).

```json
"tad": {
  "direction": "right",
  "groups": [
    {"id": "cloud", "label": "Production VPC", "style": "zone"},
    {"id": "core", "label": "Checkout core", "style": "cluster", "parent": "cloud"},
    {"id": "vendors", "label": "Vendors", "style": "external"}
  ],
  "nodes": [
    {"id": "web", "label": "Web app", "kind": "client", "tech": "Next.js"},
    {"id": "gateway", "label": "API gateway", "kind": "gateway", "tech": "Kong", "group": "cloud"},
    {"id": "orders", "label": "Order service", "kind": "service", "tech": "Go", "group": "core", "replicas": 3},
    {"id": "cards", "label": "Card processor", "kind": "card", "tech": "Stripe", "group": "vendors", "tier": 5}
  ],
  "edges": [
    {"from": "web", "to": "gateway", "label": "HTTPS"},
    {"from": "orders", "to": "bus", "label": "order.placed", "style": "async"}
  ],
  "flows": [
    {"id": "place", "label": "A shopper places an order", "path": ["web", "gateway", "orders", "payments", "cards"]}
  ]
}
```

## direction

`right` (the default) puts tiers left to right: clients on the left, data and vendors on
the right. It suits 16:9 and `wide`. `down` puts tiers top to bottom for `4:5`, `9:16`
and tall pages.

## nodes

| Key | Meaning |
| --- | --- |
| `id` | Letters, digits, `-` and `_`, starting with a letter. Ids are shared by every part. |
| `label` | Required. The component's name, 1 to 3 words: "Order service". |
| `kind` | The icon: `user`, `client`, `mobile`, `service`, `api`, `gateway`, `lb`, `cdn`, `db`, `cache`, `queue`, `stream`, `storage`, `function`, `job`, `search`, `auth`, `monitor`, `external`, `analytics`, `mail`, `card`, `model`. Default `service`. |
| `tech` | The technology in mono under the label: "PostgreSQL 16", "Kafka". |
| `group` | The group it sits in. |
| `replicas` | 2 to 99 draws a stack and a `×3` badge. |
| `tone` | A theme color for the icon: `accent`, `legacy`, `good`, `warn`, `bad`, `muted`, `ink`, `s1` to `s5`, or `c-<name>` from `palette.colors`. |
| `tier` | The column along the direction of travel, from 0. Code sets it from the edges: one tier after the furthest node that calls it. |
| `lane` | The row across it. Give it to every node or to none. |

## groups

| Style | Draws | Use for |
| --- | --- | --- |
| `zone` | a filled box | a cloud account, a VPC, a region, a data center |
| `cluster` | a box tinted with the accent | a Kubernetes cluster, a service mesh, one team's services |
| `boundary` | a dashed box | a trust boundary, a subnet, a security zone |
| `external` | a dotted box | third parties and vendors |

`parent` nests a group in another. A group with no `show` of its own appears with its
first member.

## edges

`{from, to, label, style, both, id}`. `style` is `sync` (a request: a solid line with a
filled head, the default) or `async` (an event or message: a dashed line with an open
head). `both: true` draws a head at each end. Label with the protocol or the message:
"gRPC", "POST /orders", "order.placed". The id defaults to `from-to`, such as
`gateway-orders`. An edge with no `show` of its own draws itself on once both its ends
are on screen.

## flows

`{id, label, path, tone}`. `path` lists node ids in order; each pair must be linked by
an edge in either direction, so a reply can run back along a request's line. A step's
`flow` runs a packet along every hop in turn and lights each line as it passes. A step
with no caption that runs a labelled flow takes the flow's label as its caption. Use a
second tone (`s3`) for a background flow, such as events, so the main path stays the
accent.

## states

`"state": {"cards": "down", "payments": "warn"}` in a step marks parts until a later step
sets them back to `normal`.

| State | Node | Edge |
| --- | --- | --- |
| `new` | accent outline, NEW tag | accent line |
| `legacy` | legacy-color outline, LEGACY tag | legacy-color line |
| `good` | green outline, check badge | |
| `warn` | amber outline, ! badge | |
| `bad` | red outline, × badge | red line |
| `down` | red outline, DOWN tag, contents faded | red dotted line |
| `planned` | dashed outline, PLANNED tag, contents faded | gray dashed line |

Groups take the edge states as a colored outline. Use `planned` for what a roadmap adds,
`new` for what shipped, `down` and `bad` for an incident, `legacy` for what a migration
retires.

## legend

When both edge styles appear, code adds a legend: "Request" and "Event or message".
`"legend": {"sync": "HTTP call", "async": "Kafka event"}` renames them; `false` drops it.

## Without steps

Code writes steps: each tier appears in turn, then each flow runs with its label as the
caption. Write steps by hand for anything you show to people.

## Layout

- Code places nodes in tiers from the edges and seats each one level with the parts it
  links to, so the main path reads in a straight line. Groups never overlap.
- A vendor or other `external` group that shares a column with a zone sits above or below
  it. Give its nodes a `tier` past the zone's last column to put it beside the zone, as
  the example does with `"tier": 5`.
- A TAD that does not fit the frame is shrunk; under 62 percent `build` warns that text
  is small. Fix it with a `wide` frame, `down` for tall frames, or fewer nodes.
- 6 to 14 nodes in 2 to 4 groups read well. Leave out monitoring, CI and anything the
  steps never mention; a second animation can show them.

## Writing a good TAD

1. Take the parts from a source: the design doc, the repo's services, the deploy config.
   Put the doc in `meta.sources`.
2. Name the one path the viewer must understand and make it the first flow.
3. Steps: the entry point, the main path, the side effects (events, workers), then the
   point: a failure and how the system absorbs it, or what the plan adds.
4. Captions say what happens and why it matters, in one sentence with the component
   names on screen: "When the card processor times out, Payments retries and orders
   still save."
