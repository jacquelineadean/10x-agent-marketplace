# PagerDuty recipe

## Reach
- Connector: a PagerDuty MCP server; its tool names contain `pagerduty`.
- Key for the script collector (sources 0.2.0): `PAGERDUTY_TOKEN`, a read-only REST key.

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

## Never
Acknowledge, resolve, reassign, snooze, merge or annotate an incident, or change a schedule.
