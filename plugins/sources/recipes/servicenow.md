# ServiceNow recipe

## Reach
- Connector: a ServiceNow MCP server; its tool names contain `servicenow` or `snow`.
- Script collector: `SERVICENOW_INSTANCE` with `SERVICENOW_USER` and `SERVICENOW_PASSWORD`,
  or with `SERVICENOW_TOKEN`; a read-only role.

## Facts
| Fact | How |
| --- | --- |
| Incidents by priority per month | the Aggregate API (`/api/now/stats/incident`) grouped by priority, by month opened |
| Mean time to resolve | the Aggregate API's average of business duration for resolved incidents per month |
| Changes and failed changes | `change_request` counts by month, and those closed unsuccessful |
| Open problems | `problem` counts by state at the window's end |
| Request backlog | `sc_req_item` open counts by assignment group |

Ask the Aggregate API for counts and averages. Read single records only for rows a page lists.

## queries.json
`query` holds the table and encoded query, such as
`stats incident sysparm_query=opened_at>=2026-07-01^opened_at<2026-10-01 group_by=priority`.

## Script lane
`request`: `{"table": "incident", "query": "priority=1", "date": "opened_at", "per": "month"}`
counts records through the Aggregate API; add `"avg": "calendar_stc"` for the mean of a
field instead. `query` is an encoded query; the window adds the date range.

## Never
Create, update, assign, close or comment on any record, or run a flow or script.
