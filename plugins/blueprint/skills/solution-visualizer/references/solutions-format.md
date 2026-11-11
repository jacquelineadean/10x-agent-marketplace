# The solutions file

`solutions.json` sits beside `story.json`; the story shows it with
`{"type": "solutions", "file": "solutions.json"}`, one per story. `check` refuses a file
with an error below and stops a build whose stored results are older than the file. The
excerpt shows every key; `${CLAUDE_PLUGIN_ROOT}/examples/catalog-solutions/solutions.json`
is a whole file.

```json
{
 "title": "Product page reads",
 "question": "How should the product page read price and stock?",
 "inputs": [
  {"id": "rps", "label": "Page views per second", "unit": "rps", "value": "@traffic.views_rps",
   "min": 50, "max": 3000, "step": 50, "source": "datadog"}
 ],
 "settings": [
  {"id": "ttl_s", "label": "Cache lifetime", "unit": "s", "value": 60, "min": 5, "max": 600,
   "step": 5, "key": "CATALOG_CACHE_TTL_SECONDS", "approaches": ["cache"]},
  {"id": "timeout_ms", "label": "Database timeout", "unit": "ms", "value": 250, "min": 50,
   "max": 1000, "off": 0},
  {"id": "swr", "label": "Serve the old entry while refreshing", "kind": "toggle", "value": false},
  {"id": "store_ms", "label": "View store", "kind": "choice", "value": 2,
   "options": [{"label": "In memory", "value": 2}, {"label": "On disk", "value": 8}]}
 ],
 "let": {"raw_ms": "db_ms * (1 + 3 * min(util, 3) ** 2)"},
 "scenarios": [
  {"id": "typical", "label": "Typical weekday", "text": "The weekday medians."},
  {"id": "sale", "label": "Sale peak", "inputs": {"rps": "@traffic.views_rps_sale"}}
 ],
 "measures": [
  {"id": "p95_ms", "label": "p95 page read", "unit": "ms", "better": "lower", "budget": 200,
   "feel": {"kind": "wait", "action": "Open the product page"}},
  {"id": "errors", "label": "Failed reads", "unit": "%", "decimals": 1, "budget": 1, "feel": "failures"},
  {"id": "cost", "label": "Monthly cost", "unit": "$"}
 ],
 "approaches": [
  {"id": "cache", "label": "Read through a cache", "text": "What it does and what it costs.",
   "settings": {"timeout_ms": 400},
   "let": {"miss": "min(1, keys / (ttl_s * rps))", "util": "rps * miss / (replicas * 250)"},
   "measures": {"p95_ms": "4 + raw_ms * miss", "errors": "0", "cost": "replicas * 620 + 380"}}
 ]
}
```

## Parts

| Part | Rules |
| --- | --- |
| `inputs` | Numbers the world sets: traffic, payload size, a dependency's speed. `value`, `min`, `max`, optional `step` and `decimals` (0 to 2). `source` is a story source id; without one the page says "Assumption" and the digest lists it to verify. `note` says what was measured. |
| `settings` | Numbers the team sets: one slider (`number`, the default), a `toggle` (true or false, read as 1 or 0) or a `choice` (options with number values). `approaches` limits a setting to the approaches named; every variant holds its own value. `off` is the value the formulas read when the reader turns the setting off. `key` is the configuration name it lands in. |
| `scenarios` | Named input values; inputs left out keep their own value. The first scenario is the one the page opens on and the digest's swings use. |
| `measures` | What decides the question. `better` is `lower` (default) or `higher`. `budget` is the limit a value must meet. `unit` is `ms`, `s`, `%`, `$` or a word. |
| `approaches` | 2 to 6. `measures` holds one formula per measure. `settings` overrides a setting's value for this approach. `text` says what it does and what it trades away. |
| `let` | Named formulas. Top-level names are shared; an approach's own names are private, so two approaches can each define `util`. A shared formula may read a name each approach defines for itself. |

Ids are lowercase letters, digits and underscores. Input, setting and `let` names share one
namespace because formulas read them by name.

## Feel

| `feel` | Unit | The page |
| --- | --- | --- |
| `wait` | `ms` or `s` | A button named by `action` runs one bar per compared variant for the measure's value in real time, up to 15 s, and replays when a control comes to rest. Words follow Nielsen's limits: 0.1 s reads as instant, 1 s keeps the flow of thought, 10 s holds attention. |
| `failures` | `%` | 100 requests per compared variant, with the failing share marked. |

Use `wait` for latency a person sits through and for delays such as "order confirmed".
Other measures show as a value, a bar against the largest compared value and a budget mark.

## Formulas

Python arithmetic, read by code and never run as text: numbers, names, `+ - * / % **`,
comparisons (1 or 0), `and`, `or`, `not`, `a if condition else b`, and `min`, `max`, `abs`,
`sqrt`, `log`, `exp`, `ceil`, `floor`, `round`, `clamp(x, low, high)`, `pow`.

- Every step must be a finite number at every value a control can take. `check` computes
  each approach in each scenario and at each control's `min` and `max`. Guard a division:
  `load / spare if spare > 0 else 0`, or `max(0.001, 1 - busy)`.
- Only the taken side of `if`, `and` and `or` is computed, so a guard works.
- A constant inside a formula is an assumption nobody can see or move. Make it an input.
- Keep one idea per name: `miss`, `util`, `raw_ms`. The digest shows results, not formulas.

Shapes that cover most design questions:

| Effect | Formula shape |
| --- | --- |
| Load on a resource | `util = rps / (replicas * replica_rps)` |
| Latency rising with load | `base_ms * (1 + k * min(util, 3) ** 2)` |
| Requests shed past capacity | `100 * max(0, 1 - 1 / util) if util > 0 else 0` |
| A timeout that caps the wait and fails the rest | `min(raw_ms, timeout_ms)` and `clamp(100 * (raw_ms - timeout_ms) / raw_ms, 0, 100)` |
| Cache miss share | `min(1, keys / (ttl_s * rps))` |
| Queue falling behind | `lag_s = min(3600, 0.5 / max(0.0002, 1 - min(1, writes / (consumers * rate))))` |
| Data age | `ttl_s`, or the queue's `lag_s` |
| Monthly cost | `replicas * unit_cost + fixed_cost` |
| A setting that is on or off | `0 if swr else miss` |

## What code writes

| File | Holds |
| --- | --- |
| `solutions-results.json` | Every approach at its own settings in every scenario, as facts under `solutions`, source `model`. The story lists it in `facts_file`. |
| `solutions-digest.md` | Results by scenario with budgets met or missed, the largest swings per approach and measure, and the inputs with no source. At most 12 KB. |
| `decision.md` | From `solutions decide`: the chosen settings, the model's expectations and the acceptance checks. See `implement.md`. |

A warning that a control "changes no measure" means a formula does not read it: fix the
formula or remove the control.
