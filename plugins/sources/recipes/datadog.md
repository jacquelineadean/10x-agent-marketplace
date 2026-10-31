# Datadog recipe

## Reach
- Connector: the Datadog connector or MCP server; its tool names contain `datadog`.
- Keys for the script collector (sources 0.2.0): `DD_API_KEY` with `DD_APP_KEY` (or `DD_APPLICATION_KEY`), and `DD_SITE`.

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

## Never
Create, edit, mute or delete a monitor, dashboard, notebook, SLO or incident.
