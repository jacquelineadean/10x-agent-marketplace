# briefing

Slide decks and KPI dashboards from facts, as claude.ai Artifacts. Built on
`chronicle-engine` under [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md) and
[spec 002](../../specs/002-chronicle-split/spec.md). Installing briefing installs the
[sources](../sources/README.md) plugin, whose gatherer reads company systems.

| Skill | Default output | Options |
| --- | --- | --- |
| `/briefing:deck` | fixed 16:9 slides on a horizontal track: arrows, keys and swipes, a counter, an overview grid, speaker notes, builds, and animations that step per click | claude.ai Slides (`export --to slides`), a PDF and a PNG per slide (`slides --pdf --png`) |
| `/briefing:dashboard` | KPI tiles with value, target, status by rule, change and sparkline; charts, tables, filters over precomputed slices; an as-of stamp; the query behind each number on hover | claude.ai's Dashboard type (`export --to dashboard`) |

Every number is a fact token with its source and query; code computes, formats and judges
it. A brand kit (`--brand run|repo|config|PATH`) gives every page the same colors and type.

## Command line
```bash
plugins/briefing/scripts/briefing new briefing-runs/q4 --layout deck --title "Q4 review"
plugins/briefing/scripts/briefing check briefing-runs/q4/story.json
plugins/briefing/scripts/briefing build briefing-runs/q4/story.json
plugins/briefing/scripts/briefing slides briefing-runs/q4/story.json --png --pdf
plugins/briefing/scripts/briefing export briefing-runs/q4/story.json --to slides
plugins/briefing/scripts/briefing sources detect --picker
```

## Examples
Both use the Keystone example's facts (invented data), a `queries.json` and Fernhill's
brand kit.
- `examples/keystone-deck/`: a decision deck with KPIs, a build, a chart, a stepped
  animation (build it first: `briefing animate build anim/animation.json --out build/anim
  --formats svg`) and a risk table.
- `examples/keystone-dashboard/`: six KPI tiles, two charts, a rollout chart filtered by
  state, a cost chart and a journey table.

## Files
| Path | Holds |
| --- | --- |
| `skills/deck/`, `skills/dashboard/` | the two skills and their format references |
| `references/` | how decks and dashboards read (`voice.md`) and brand kits (`brand.md`) |
| `scripts/briefing` | launcher used through `${CLAUDE_PLUGIN_ROOT}` |
| `src/briefing/` | the pack: deck and dashboard layouts, the kpi, filters and animation blocks, checks, exports and commands; `assets/` holds their CSS and scripts |
| `src/chronicle_engine`, `src/sources` | links to the shared engine and sources packages; Claude Code copies linked files at install |
| `examples/` | the keystone deck and dashboard |
| `tests/` | `test_briefing_*.py`; builds run in their own process |
