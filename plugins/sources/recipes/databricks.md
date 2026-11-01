# Databricks recipe

## Reach
- Connector: a Databricks MCP server (the workspace's managed SQL or Unity Catalog servers);
  its tool names contain `databricks`.
- Script collector: `DATABRICKS_HOST` and `DATABRICKS_TOKEN` for a read-only principal, and
  a SQL warehouse id in the request or the named connection's HTTP path.

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

## Script lane
`request` is one of:
- `{"sql": "SELECT date_trunc('MONTH', ordered_at) AS month, count(*) AS orders FROM
  gold.orders WHERE ordered_at >= :start AND ordered_at < :until GROUP BY 1 ORDER BY 1",
  "warehouse": "<warehouse id>"}`: runs through Statement Execution with a 30-second wait
  that cancels it. `:start`, `:end` and `:until` come from the window; `params` names more.
- `{"lineage": "main.sales.orders"}`: upstream and downstream table names.

One cell becomes one fact; any other result becomes one list per column under the
entry's path (`databricks.orders.month`, `databricks.orders.orders`), so name every column. The
collector refuses a statement that writes, more than one statement and more than
10,000 rows, and stops one that runs past 30 seconds.

## Never
Start, stop or edit a warehouse, cluster, job or pipeline, or write to any table or volume.
