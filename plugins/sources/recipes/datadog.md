# Datadog recipe

## Reach
- Connector: the Datadog connector or MCP server; its tool names contain `datadog`.
- Script collector: `DD_API_KEY` with `DD_APP_KEY` (or `DD_APPLICATION_KEY`), and `DD_SITE`.

## Facts
| Fact | How |
| --- | --- |
| SLO status per service | SLO history: 30-day availability per month, with the target |
| Latency | APM p95 per month for the main endpoints |
| Error rate during an incident | metric query at one-minute resolution over the incident window |
| Traffic share | request counts by service or tag per month; shares go in `derive` |
| Incidents | count by severity in the window; the timeline of the worst one from its postmortem |
| Page speed | RUM p75 of a view's loading time per day |

Ask for rollups the tool computes (`.rollup(avg, 86400)`, percentiles, counts). Never page
through raw events, spans or logs.

## queries.json
`query` holds the metric, SLO or RUM query with its rollup, such as
`p95:trace.http.request.duration{service:checkout}.rollup(avg, 2592000)`.

## Script lane
`request` is one of:
- `{"metric": "sum:trace.http.request.hits{service:checkout}", "reduce": "sum", "per": "month"}`:
  daily rollups, reduced per period by `avg`, `sum`, `max`, `min` or `last`. Leave out
  `.rollup()`; aggregate across groups so the query returns one series.
- `{"slo": "<slo id>", "per": "month"}`: the SLI for each period.
- `{"rum": "@type:view @view.name:/checkout", "measure": "@view.loading_time",
  "aggregation": "pc75", "per": "week"}`: computed in Datadog for each period.

## Never
Create, edit, mute or delete a monitor, dashboard, notebook, SLO or incident.
