# GitHub recipe

## Reach
- Connector: the GitHub connector or GitHub MCP server; its tool names contain `github`.
- Keys for the script collector (sources 0.2.0): `GITHUB_TOKEN` or `GH_TOKEN`, or a signed-in `gh`.

## Facts
| Fact | How |
| --- | --- |
| Pull requests merged per week or month | search `is:pr is:merged merged:START..END` per period; read the total count |
| Production deploys per day or week | deployments or releases of the service repos, or runs of the deploy workflow, counted by date |
| Lead time for changes | for a sample of merged pull requests, first commit to merge; record the sample size in the note |
| First-review wait | pull request opened to first review, over the window |
| Contributors | distinct authors of merged pull requests in the window |
| Repositories touched | distinct repositories with merged pull requests |

Medians and averages over a sample go in the `derive` table or a short script, never in your head.

## queries.json
`query` holds the search string or API path with its parameters, such as
`search_issues q="is:pr is:merged merged:2026-07-01..2026-09-30 org:acme"`; `connection`
holds the server name.

## Never
Comment, review, label, merge, close, push, or open an issue or pull request.
