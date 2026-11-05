# blueprint

Interactive system and data design visuals and clickable prototypes, built on
`chronicle-engine` under [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md) and
[spec 002](../../specs/002-chronicle-split/spec.md). Installing blueprint installs the
[sources](../sources/README.md) plugin for company facts.

| Skill | Makes |
| --- | --- |
| `/blueprint:architecture` | technical architecture diagrams (TADs) written as data and laid out in code, sequence diagrams and ERDs, each one SVG that plays step by step; and pages where parts open their details, pins mark decisions and a player steps through the flows |
| `/blueprint:prototype` | clickable screens behind tabs with cards, lists, tables and charts fed by facts, links between screens, and desktop and phone widths |

Every figure exports SVG, HTML, PNG, GIF and MP4 (`animate build --formats`). A briefing
deck plays a blueprint SVG one step per click.

## Install

```text
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install blueprint@10x-agent-marketplace
```

Installing blueprint installs sources with it.

## Command line
```bash
plugins/blueprint/scripts/blueprint animate new blueprint-runs/checkout --kind tad --title "Checkout"
plugins/blueprint/scripts/blueprint animate build examples/animation-tad/animation.json --formats svg,html,png
plugins/blueprint/scripts/blueprint schema examples/orders-erd/schema.csv --out erd.json
plugins/blueprint/scripts/blueprint schema --connection postgres --schema public --out erd.json
plugins/blueprint/scripts/blueprint lineage main.sales.orders --out lineage/animation.json
plugins/blueprint/scripts/blueprint new blueprint-runs/console --layout prototype --title "Console"
plugins/blueprint/scripts/blueprint build blueprint-runs/console/story.json
```

## Examples (invented data)
| Folder | Shows |
| --- | --- |
| `examples/animation-tad/` | an order's path through a checkout system: 10 components in 4 groups, 3 flows, a card processor going down and a planned fraud check (moved from chronicle) |
| `examples/checkout-sequence/` | the same order as a sequence: 5 participants, 7 messages in 3 steps |
| `examples/orders-erd/` | 5 tables and 4 relations, generated from `schema.csv` with `blueprint schema` |
| `examples/checkout-architecture/` | the TAD on a page with part details, 2 pins and the step player; build `tad/animation.json` to `build/tad/` first |
| `examples/oncall-prototype/` | an on-call console: 4 screens, cards that open screens, incident rows that open their notes |

## Files
| Path | Holds |
| --- | --- |
| `skills/architecture/`, `skills/prototype/` | the two skills and their references (`tad.md`, `sequence.md`, `erd.md`, `architecture-format.md`, `prototype-format.md`) |
| `scripts/blueprint` | launcher used through `${CLAUDE_PLUGIN_ROOT}` |
| `src/blueprint/` | the pack: the TAD (`core/tad/`), sequence and ERD kinds, the architecture, cards and list blocks, the prototype layout, checks, `schema` (CSV or a live Postgres or Oracle read through the sources package) and `lineage` (a TAD from Unity Catalog lineage); `assets/` holds their CSS and scripts and the TAD stylesheet |
| `src/chronicle_engine`, `src/sources` | links to the shared engine and sources packages |
| `examples/`, `tests/` | the examples above; `test_blueprint_*.py`, with builds in their own process |
