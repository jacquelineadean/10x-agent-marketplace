# Oracle recipe

## Reach
- Connector: an Oracle MCP server (SQLcl's `sql -mcp` server) in the session, or the
  `sources-db` agent that `/sources:connect --agent` writes; tool names contain `oracle` or `sqlcl`.
- Keys for the script collector (sources 0.2.0): `ORACLE_USER`, `ORACLE_PASSWORD` and
  `ORACLE_DSN`, read through the installed SQLcl (`sql`).

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
