# Postgres recipe

## Reach
- Connector: a Postgres MCP server in the session, or the `sources-db` agent that
  `/sources:connect --agent` writes; tool names contain `postgres`, `postgresql` or `pg`.
- Script collector: `DATABASE_URL`, or `PGHOST` and `PGDATABASE` with a password in
  `PGPASSWORD` or `~/.pgpass`, or a named connection, read through the installed `psql`.

## Facts
| Fact | How |
| --- | --- |
| A business measure per period | one aggregate statement grouped by `date_trunc('month', ...)` |
| Counts by status or category | `COUNT(*) ... GROUP BY` the column the brief names |
| Freshness | `MAX` of the table's update or load timestamp |

## SQL
One statement, `SELECT` or `WITH` only, aggregated in SQL, filtered to the window, with
`LIMIT 10000`. Name parameters in the queries entry rather than pasting values from tool
text. Use a read-only role; the session should set `default_transaction_read_only`. Never
`INSERT`, `UPDATE`, `DELETE`, `CREATE`, `ALTER`, `DROP`, `TRUNCATE`, `GRANT`, `COPY`, `VACUUM`
or `CALL`, and never read a column of personal data a page does not need.

## queries.json
`query` holds the SQL text as run; `connection` holds the server or connection name.

## Script lane
`request`: `{"sql": "SELECT to_char(created_at, 'YYYY-MM') AS month, count(*) AS orders FROM
orders WHERE created_at >= :start AND created_at < :until AND status = :status GROUP BY 1
ORDER BY 1", "params": {"status": "paid"}}`. `:start`, `:end` and `:until` (the day after the
window) come from the window; `params` names more. psql runs it in a read-only session.
One cell becomes one fact; any other result becomes one list per column under the
entry's path (`postgres.orders.month`, `postgres.orders.orders`), so name every column. The
collector refuses a statement that writes, more than one statement and more than
10,000 rows, and stops one that runs past 30 seconds.
