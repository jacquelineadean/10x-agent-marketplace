# Sequence diagrams (`kind: "sequence"`)

```json
"sequence": {
  "participants": [{"id": "web", "label": "Web app"}, {"id": "api", "label": "Order API"}],
  "messages": [
    {"from": "web", "to": "api", "label": "POST /orders"},
    {"from": "api", "to": "api", "label": "save order"},
    {"from": "api", "to": "web", "label": "201 Created", "kind": "reply"}
  ]
}
```

- Participants sit left to right in the order given, each with a lifeline. 2 to 7 fit a
  16:9 frame.
- A message is `sync` (default: solid line, filled head), `async` (solid line, open head)
  or `reply` (dashed, open head). A message to itself draws a loop.
- Ids for steps: `p-<participant id>` for a participant and its lifeline, `m1`, `m2`, ... for
  messages in order (or a message's own `id`), and `m1-path` for the path a packet runs.
- With no `steps`, every participant shows first and each message plays in its own step,
  captioned with its label. Write steps to group messages into beats:
  `{"caption": "...", "draw": ["m3", "m4"], "flow": ["m4-path"]}`.
- Labels may hold fact tokens; keep each under about 24 characters.
