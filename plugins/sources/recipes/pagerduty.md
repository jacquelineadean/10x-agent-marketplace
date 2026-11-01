# PagerDuty recipe

## Reach
- Connector: a PagerDuty MCP server; its tool names contain `pagerduty`.
- Script collector: `PAGERDUTY_TOKEN`, a read-only REST key.

## Facts
| Fact | How |
| --- | --- |
| Incidents by urgency per month | incidents in the window, counted by urgency and month |
| Time to acknowledge and to resolve | the analytics endpoints' medians per service, when the tool offers them |
| Pages out of hours | incidents created outside the team's working hours, counted per month |
| On-call load | incidents per responder per week, as counts |

## queries.json
`query` holds the call and filters, such as
`list_incidents since=2026-07-01 until=2026-09-30 service_ids=[PX1] urgency=high`.

## Script lane
`request`: `{"incidents": {"urgencies": ["high"], "service_ids": ["P1ABC"], "statuses":
["resolved"]}, "per": "month"}` counts incidents created in each period; `{}` filters
nothing. Without `per` the entry writes one count for the window; with it, a list per period beside the period labels.

## Never
Acknowledge, resolve, reassign, snooze, merge or annotate an incident, or change a schedule.
