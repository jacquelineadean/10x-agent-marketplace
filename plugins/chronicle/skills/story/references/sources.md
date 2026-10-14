# What to gather from each tool

The gatherer works read-only, asks for counts and aggregates instead of full records,
and pages in small batches. It records each source in the story's `sources` list with an
`as_of` date. Pull only what the outline needs; a status page rarely needs more than
thirty facts and eight series.

## GitHub (or GitHub Enterprise)

| Fact | How |
| --- | --- |
| Pull requests merged per week or month | search `is:pr is:merged merged:START..END` per period, read the total count |
| Production deploys per day or week | deployments API or releases list for the service repos; or the CI workflow that deploys, counted by run date |
| Lead time for changes | for a sample of merged PRs: first commit to merge, median; say the sample size in the note |
| First-review wait | PR created to first review, median over the window |
| Contributors | distinct authors of merged PRs in the window |
| Repositories touched | distinct repos with merged PRs |

## Jira

| Fact | How |
| --- | --- |
| Sprint velocity and scope | closed sprints in order: completed points, committed points, total scope at sprint end |
| Epics by status | JQL `project = KEY AND issuetype = Epic`, counted by status category |
| Milestones and dates | fix versions or epics with due dates; change tickets for cutovers and freezes |
| Risks | issues with a risk label or type: title, likelihood, impact, owner |

## Confluence

Decision records, RFCs, launch notes and postmortems: dates, titles and one-line
summaries for the timeline. Quote a document only in a `quote` block, attributed, and only
words actually written there.

## Datadog

| Fact | How |
| --- | --- |
| SLO status per service | SLO history: 30-day availability per month and the target |
| Latency | APM p95 per month for the main endpoints |
| Error rate during an incident | metric query at one-minute resolution for the incident window |
| Traffic share | request counts by service or tag per month, as percent of the total |
| Incidents | count by severity in the window; the timeline of the worst one from its postmortem |

## PagerDuty

Incidents by urgency per month, median time to acknowledge and to resolve, pages out of
hours. Use these for reliability chapters and on-call health.

## Files and pasted notes

CSV and spreadsheets: read the columns the outline needs and store them as series.
Meeting notes, status emails and plans: extract dates, owners, decisions and stated
numbers; the source `detail` says which document each came from.

## Costs and business numbers

Finance and analytics numbers rarely sit in a connected tool. Ask the user for them or
use the figures they paste; mark each with its source and period.
