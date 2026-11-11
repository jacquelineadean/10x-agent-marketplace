# Jira recipe

## Reach
- Connector: the Atlassian connector or a Jira MCP server; its tool names contain `atlassian` or `jira`.
- Script collector: `JIRA_URL`, `JIRA_EMAIL` and `JIRA_API_TOKEN`.

## Facts
| Fact | How |
| --- | --- |
| Sprint velocity and scope | closed sprints in order: completed points, committed points, scope at sprint end |
| Epics by status | JQL `project = KEY AND issuetype = Epic`, counted by status category |
| Milestones and dates | fix versions or epics with due dates; change tickets for cutovers and freezes |
| Risks | issues with a risk label or type: title, likelihood, impact, owner |
| Flow | issues created and resolved per week; open count at each week's end |

Use search totals and counts. Fetch issue fields only for the rows a page lists, such as risks.

## queries.json
`query` holds the JQL or the board and sprint call, such as
`JQL project = SHOP AND issuetype = Epic AND statusCategory = Done`.

## Script lane
`request`: `{"jql": "project = SHOP AND statusCategory = Done", "date": "resolved", "per": "week"}`
counts the issues whose `date` field falls in each period (default `created`). Jira Cloud
counts through its read-only approximate-count query. Without `per` the entry writes one count for the window; with it, a list per period beside the period labels.

## Never
Create, edit, transition, assign, comment on or log work against any issue.
