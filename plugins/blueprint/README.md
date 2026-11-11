# blueprint

Interactive system and data design visuals and clickable prototypes, built on
`chronicle-engine` under [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md) and
[spec 002](../../specs/002-chronicle-split/spec.md). Installing blueprint installs the
[sources](../sources/README.md) plugin for company facts.

| Skill | Makes |
| --- | --- |
| `/blueprint:architecture` | technical architecture diagrams (TADs) written as data and laid out in code, sequence diagrams and ERDs, each one SVG that plays step by step; and pages where parts open their details, pins mark decisions and a player steps through the flows |
| `/blueprint:prototype` | clickable screens behind tabs with cards, lists, tables and charts fed by facts, links between screens, and desktop and phone widths |
| `/blueprint:solution-visualizer` | a page that compares 2 to 6 approaches to one design question: sliders for inputs, settings per approach to change, turn off or copy into variants, scenarios to switch and save, measures against budgets, a wait played in real time and failures out of 100 requests; then `decision.md`, from which Claude implements the chosen approach with the chosen settings |

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
plugins/blueprint/scripts/blueprint solutions new blueprint-runs/reads --title "Product page reads"
plugins/blueprint/scripts/blueprint solutions simulate blueprint-runs/reads/story.json
plugins/blueprint/scripts/blueprint solutions decide blueprint-runs/reads/story.json --decision blueprint-runs/reads/decision.json
```

## Solution visualizer
`/blueprint:solution-visualizer` answers "which approach, with which settings" before any
code changes, then hands the answer to the implementation.

1. Claude writes `solutions.json`: approaches, inputs, settings, scenarios, and one formula
   per measure and approach. Formulas are arithmetic text that code reads into a tree and
   never runs as text.
2. `solutions simulate` computes every approach in every scenario and writes
   `solutions-results.json` (facts the story cites through tokens) and
   `solutions-digest.md` (at most 12 KB, the only file Claude reads).
3. `build` renders the page. Its script walks the same formula trees as a reader moves a
   control, and compares its first numbers with the build's; a difference shows on the page.
4. A reader moves inputs, changes or turns off settings, adds variants, switches and saves
   scenarios, runs the wait, presses Choose and copies the decision as JSON.
5. `solutions decide` checks the export against the file and writes `decision.md`: each
   setting with its decided value and configuration key, the model's numbers per scenario,
   one acceptance check per budget and scenario, and the inputs with no source.
6. Claude implements from `decision.md` after the user confirms the plan.

| Who | Model | Does |
| --- | --- | --- |
| `blueprint:solution-scout` | Haiku, with Read, Grep, Glob and Write | finds the request's path, settings, limits and stated numbers in a repository and writes `context.md` (8 KB) or `locate.md` (6 KB) |
| `sources:gatherer` | Sonnet | reads traffic and timings from company systems into `facts.json` |
| the session itself | the user's model | writes the model, reads the digest, implements the decision |

The feature adds no hook and no MCP server. A plugin hook runs in every session from
session load, and this workflow starts only when a user asks for it. The page reads
nothing after it loads.

Manual test: `claude --plugin-dir plugins/blueprint`, then
`/blueprint:solution-visualizer how should the product page read price and stock`. Confirm
the page opens with three approaches, a slider changes the numbers, "Open the product page"
runs the bars, and pasting the copied decision back produces `decision.md`.

## Examples (invented data)
| Folder | Shows |
| --- | --- |
| `examples/animation-tad/` | an order's path through a checkout system: 10 components in 4 groups, 3 flows, a card processor going down and a planned fraud check (moved from chronicle) |
| `examples/checkout-sequence/` | the same order as a sequence: 5 participants, 7 messages in 3 steps |
| `examples/orders-erd/` | 5 tables and 4 relations, generated from `schema.csv` with `blueprint schema` |
| `examples/checkout-architecture/` | the TAD on a page with part details, 2 pins and the step player; build `tad/animation.json` to `build/tad/` first |
| `examples/oncall-prototype/` | an on-call console: 4 screens, cards that open screens, incident rows that open their notes |
| `examples/catalog-solutions/` | three ways to read price and stock on a product page: 5 inputs, 6 settings, 4 scenarios, 4 measures, each approach missing a budget in a different scenario; with its results, digest and an exported `decision.json` |

## Files
| Path | Holds |
| --- | --- |
| `skills/architecture/`, `skills/prototype/`, `skills/solution-visualizer/` | the three skills and their references (`tad.md`, `sequence.md`, `erd.md`, `architecture-format.md`, `prototype-format.md`, `solutions-format.md`, `implement.md`) |
| `agents/solution-scout.md` | the Haiku subagent that reads a repository for the solution visualizer |
| `scripts/blueprint` | launcher used through `${CLAUDE_PLUGIN_ROOT}` |
| `src/blueprint/` | the pack: the TAD (`core/tad/`), sequence and ERD kinds, the architecture, cards and list blocks, the prototype layout, the solutions block with its formula reader, simulator, digest and decision (`core/solutions/`), checks, `schema` (CSV or a live Postgres or Oracle read through the sources package), `lineage` (a TAD from Unity Catalog lineage) and `solutions`; `assets/` holds their CSS and scripts and the TAD stylesheet |
| `src/chronicle_engine`, `src/sources` | links to the shared engine and sources packages |
| `examples/`, `tests/` | the examples above; `test_blueprint_*.py`, with builds in their own process |
