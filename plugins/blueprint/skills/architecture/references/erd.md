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
Export one row per column with its key and reference, then run
`blueprint schema export.csv --out erd.json` and copy the object into the animation. For
Postgres, run this read-only query with `psql --csv` (or ask `sources:gatherer`):

```sql
SELECT c.table_name AS "table", c.column_name AS "column", c.data_type AS "type",
       CASE WHEN tc.constraint_type = 'PRIMARY KEY' THEN 'pk'
            WHEN tc.constraint_type = 'FOREIGN KEY' THEN 'fk' ELSE '' END AS "key",
       CASE WHEN tc.constraint_type = 'FOREIGN KEY'
            THEN ccu.table_name || '.' || ccu.column_name ELSE '' END AS "references"
FROM information_schema.columns c
LEFT JOIN information_schema.key_column_usage kcu
  ON kcu.table_schema = c.table_schema AND kcu.table_name = c.table_name
 AND kcu.column_name = c.column_name
LEFT JOIN information_schema.table_constraints tc
  ON tc.constraint_name = kcu.constraint_name AND tc.table_schema = kcu.table_schema
LEFT JOIN information_schema.constraint_column_usage ccu
  ON ccu.constraint_name = tc.constraint_name AND tc.constraint_type = 'FOREIGN KEY'
WHERE c.table_schema = 'public'
ORDER BY c.table_name, c.ordinal_position
LIMIT 10000;
```
