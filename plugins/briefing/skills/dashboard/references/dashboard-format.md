# The dashboard file

A dashboard is a story file with `"layout": "dashboard"`. Read
`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/blocks.md` for tokens, formats and the
blocks every layout shares, and `${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/facts.md`
for the facts file.

```json
{
  "schema_version": 1,
  "layout": "dashboard",
  "meta": {"title": "...", "kicker": "...", "dek": "...", "as_of": "2026-10-14"},
  "sources": [{"id": "datadog", "label": "Datadog", "detail": "...", "as_of": "2026-10-14"}],
  "chapters": [{"id": "headline", "title": "Headline measures", "dek": "...", "blocks": [ ... ]}]
}
```

| Key | Meaning |
| --- | --- |
| `meta.as_of` | With the sources' ISO `as_of` dates, sets the header's as-of stamp (the latest). |
| `chapters[]` | Sections, each with a heading and a grid of blocks. |
| `"span": 1` or `2` on a block | Its width in the two-column grid. `kpi`, `filters`, `table`, `stats`, `timeline` and `roadmap` span both by default. |
| `"slice": "key"` on a block | One copy per option of that filter; see below. |

### kpi
`{"type": "kpi", "items": [{"label", "value": "@path", "target": number or "@path", "better": "up" | "down", "warn": 10, "change": "@path", "spark": "@series", "format", "note"}]}`.
Code sets each tile's status: on target, near target (within `warn` percent, 10 by
default) or off target, shown as a colored rule, a dot and a word. Every value needs a
target and a query in `queries.json`; `check` errors without a target and warns without a
query.

### filters
`{"type": "filters", "by": [{"key": "team", "label": "Team", "options": {"payments": "Payments", "search": "Search"}, "default": "payments"}]}`.
Controls that pick an option. A block with `"slice": "team"` writes `{team}` where its fact
paths change (`"value": "@delivery.{team}.deploys"`); the build renders one copy per option
and the page shows the chosen one. Every option's facts must exist; `check` names any that
do not.

## Staleness
`check` warns when a system's newest query in `queries.json` is more than 7 days old.
Gather again before publishing.
