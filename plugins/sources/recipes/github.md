# GitHub recipe

## Reach
- Connector: the GitHub connector or GitHub MCP server; its tool names contain `github`.
- Script collector: `GITHUB_TOKEN` or `GH_TOKEN`, or a signed-in `gh`.

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

## Script lane
`request` is one of:
- `{"search": "is:pr is:merged org:acme", "date": "merged", "per": "week"}`: the search
  total; `date` is `created`, `merged`, `closed` or `updated`, and the window fills it in.
- `{"runs": "acme/shop", "workflow": "deploy.yml", "status": "success", "branch": "main"}`:
  workflow runs created in the window.

Without `per` the entry writes one count for the window; with it, a list per period beside the period labels.

## Never
Comment, review, label, merge, close, push, or open an issue or pull request.
