# Entity relationship diagrams (`kind: "erd"`)

```json
"erd": {
  "entities": [
    {"id": "customers", "columns": [{"name": "id", "type": "bigint", "key": "pk"}]},
    {"id": "orders", "columns": [{"name": "id", "type": "bigint", "key": "pk"},
                                {"name": "customer_id", "type": "bigint", "key": "fk"}]}
  ],
  "relations": [{"from": "orders.customer_id", "to": "customers.id", "kind": "many-to-one", "label": "placed by"}]
}
```

- Tables sit in rows as wide as the frame allows; relation lines run only in the gaps
  between tables and end in a crow's foot (many) or a bar (one).
- `kind` is `one-to-one`, `one-to-many`, `many-to-one` (default) or `many-to-many`.
- Show the columns a reader needs (keys and the ones the story is about), at most 8 a table.
- Ids for steps: `e-<table id>` for a table, `r1`, `r2`, ... for relations in order, and
  `r1-path` for a packet's path. With no `steps`, the tables show, then the keys draw.

## From a database
Read the catalog live through the sources package (psql for Postgres, SQLcl for Oracle;
read-only session, 30-second limit):

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" schema --connection postgres --schema public --out erd.json
```

`--connection` is `postgres`, `oracle` or a connection named with `sources connection
add`. Without keys, export one row per column with its key and reference as CSV and run
`blueprint schema export.csv --out erd.json`. For Postgres, export this query with
`psql --csv`; it reads `pg_catalog`, because `information_schema` hides constraints from a
role that may only SELECT:

```sql
SELECT c.relname AS "table", a.attname AS "column",
       format_type(a.atttypid, a.atttypmod) AS "type",
       CASE WHEN pk.conname IS NOT NULL THEN 'pk'
            WHEN fk.conname IS NOT NULL THEN 'fk' ELSE '' END AS "key",
       CASE WHEN fk.conname IS NOT NULL THEN rt.relname || '.' || ra.attname
            ELSE '' END AS "references"
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
LEFT JOIN pg_constraint pk
  ON pk.conrelid = c.oid AND pk.contype = 'p' AND a.attnum = ANY (pk.conkey)
LEFT JOIN pg_constraint fk
  ON fk.conrelid = c.oid AND fk.contype = 'f' AND a.attnum = ANY (fk.conkey)
LEFT JOIN pg_class rt ON rt.oid = fk.confrelid
LEFT JOIN pg_attribute ra
  ON ra.attrelid = fk.confrelid AND ra.attnum = fk.confkey[array_position(fk.conkey, a.attnum)]
WHERE n.nspname = 'public' AND c.relkind IN ('r', 'p', 'v', 'm')
ORDER BY c.relname, a.attnum;
```

Copy the `erd` object into the animation, then keep the tables the story needs.
