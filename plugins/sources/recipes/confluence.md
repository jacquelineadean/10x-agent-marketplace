# Confluence recipe

## Reach
- Connector: the Atlassian connector or a Confluence MCP server; its tool names contain `atlassian` or `confluence`.
- Keys for the script collector (sources 0.2.0): `CONFLUENCE_URL`, `CONFLUENCE_EMAIL` and `CONFLUENCE_API_TOKEN`.

## Facts
Decision records, RFCs, launch notes and postmortems give dates, titles and one-line
summaries for a timeline. Store each as a record: the date as `value`, the title and
summary in `note`, the page title in the queries entry.

Quote a page only word for word, in a record whose `note` says who wrote it and where,
and only when the brief asks for quotes.

## queries.json
`query` holds the CQL or the page id, such as
`CQL type = page AND space = ENG AND label = "postmortem" AND created >= 2026-07-01`.

## Never
Create, edit, move, comment on or restrict a page.
