# Confluence recipe

## Reach
- Connector: the Atlassian connector or a Confluence MCP server; its tool names contain `atlassian` or `confluence`.
- Script collector: `CONFLUENCE_URL`, `CONFLUENCE_EMAIL` and `CONFLUENCE_API_TOKEN`.

## Facts
Decision records, RFCs, launch notes and postmortems give dates, titles and one-line
summaries for a timeline. Store each as a record: the date as `value`, the title and
summary in `note`, the page title in the queries entry.

Quote a page only word for word, in a record whose `note` says who wrote it and where,
and only when the brief asks for quotes.

## queries.json
`query` holds the CQL or the page id, such as
`CQL type = page AND space = ENG AND label = "postmortem" AND created >= 2026-07-01`.

## Script lane
`request`: `{"cql": "space = ENG AND type = page", "date": "created", "per": "month"}`
counts pages by `created` or `lastmodified`. Without `per` the entry writes one count for the window; with it, a list per period beside the period labels.

## Never
Create, edit, move, comment on or restrict a page.
