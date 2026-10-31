# The prototype file

A story file with `"layout": "prototype"`. `meta.title` names the app; each chapter is a
screen behind a tab (`short` labels the tab). Blocks sit in a two-column grid; `"span": 2`
widens one, and cards, lists and tables span both by default.

### cards
`{"type": "cards", "items": [{"title", "value": "{{fact}}", "text", "status": "good" | "warn" | "bad", "link": "screen id"}]}`.
A card with `link` opens that screen.

### list
`{"type": "list", "items": [{"title", "meta", "status", "text", "link"}]}`.
A row with `link` opens that screen; a row with `text` opens its text in place.

Use `table`, `chart`, `stats`, `timeline`, `widget` and the other engine blocks inside a
screen as on any page. `check` refuses a link to a screen that does not exist.
