# Oracle recipe

## Reach
- Connector: an Oracle MCP server (SQLcl's `sql -mcp` server) in the session, or the
  `sources-db` agent that `/sources:connect --agent` writes; tool names contain `oracle` or `sqlcl`.
- Script collector: `ORACLE_USER`, `ORACLE_PASSWORD` and `ORACLE_DSN` (`host:port/service`
  or a TNS alias), or a named connection, read through the installed SQLcl (`sql`).

## Facts
| Fact | How |
| --- | --- |
| A business measure per period | one aggregate statement grouped by `TRUNC(date_column, 'MM')` |
| Counts by status or category | `COUNT(*) ... GROUP BY` the column the brief names |
| Freshness | `MAX` of the table's update or load timestamp |

## SQL
One statement, `SELECT` or `WITH` only, aggregated in SQL, filtered to the window, with
`FETCH FIRST 10000 ROWS ONLY`. Start the session with `SET TRANSACTION READ ONLY`. Never
`INSERT`, `UPDATE`, `DELETE`, `MERGE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `GRANT` or a
PL/SQL block, and never read a column of personal data a page does not need.

## queries.json
`query` holds the SQL text as run; `connection` holds the server or connection name.

## Script lane
`request`: `{"sql": "SELECT TO_CHAR(created_at, 'YYYY-MM') AS month, COUNT(*) AS orders FROM
orders WHERE created_at >= TO_DATE(:start, 'YYYY-MM-DD') GROUP BY TO_CHAR(created_at,
'YYYY-MM') ORDER BY 1"}`. Parameters arrive as text binds, so wrap dates in `TO_DATE`. SQLcl
runs it in a `SET TRANSACTION READ ONLY` transaction.
One cell becomes one fact; any other result becomes one list per column under the
entry's path (`oracle.orders.month`, `oracle.orders.orders`), so name every column. The
collector refuses a statement that writes, more than one statement and more than
10,000 rows, and stops one that runs past 30 seconds.
