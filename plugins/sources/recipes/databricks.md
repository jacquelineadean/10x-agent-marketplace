# Databricks recipe

## Reach
- Connector: a Databricks MCP server (the workspace's managed SQL or Unity Catalog servers);
  its tool names contain `databricks`.
- Keys for the script collector (sources 0.2.0): `DATABRICKS_HOST` and `DATABRICKS_TOKEN` for
  a read-only principal, or a signed-in `databricks` program.

## Facts
| Fact | How |
| --- | --- |
| A business measure per period | one aggregate SQL statement on a SQL warehouse, grouped by month |
| Table freshness | the latest load timestamp of each table the page names |
| Job health | job runs in the window counted by result state |
| Lineage | Unity Catalog lineage of the tables the page names: upstream and downstream names |

## SQL
One statement, `SELECT` or `WITH` only, aggregated in SQL (`COUNT`, `SUM`, `AVG`,
`percentile_approx`, `date_trunc`), filtered to the window, with `LIMIT 10000`. Use the
views or tables the brief or connection names. Never `INSERT`, `UPDATE`, `DELETE`, `MERGE`,
`CREATE`, `ALTER`, `DROP`, `GRANT`, `OPTIMIZE` or `COPY`.

## queries.json
`query` holds the SQL text as run; `connection` holds the server or connection name.

## Never
Start, stop or edit a warehouse, cluster, job or pipeline, or write to any table or volume.
