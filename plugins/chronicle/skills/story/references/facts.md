# The facts file

`facts.json` holds every number and date the page shows, each with where it came from.
The story points into it; the page never shows a number that is not here.

## Shape

Group facts by subject. A fact is a record or a bare value; series are arrays.

```json
{
  "project": {
    "as_of": {"value": "2026-10-14", "source": "jira"},
    "engineers": {"value": 25, "unit": "engineers", "source": "jira"}
  },
  "delivery": {
    "month": ["2026-07", "2026-08", "2026-09"],
    "deploys_per_week": [31, 34, 37],
    "deploys_now": {"value": 37, "unit": "per week", "source": "github",
                    "note": "production deploys, September 2026 weekly average"}
  },
  "derive": { ... }
}
```

| Field | Meaning |
| --- | --- |
| `value` | Number, ISO date (`2026-11-03`, `2026-11`) or short text. |
| `unit` | `%`, `x`, `$`, `ms`, `min`, `pts`, `pp` or a plural word (`days`, `engineers`). |
| `source` | The `id` of a source in the story's `sources` list. |
| `note` | What exactly was measured, over which period. Shown on hover. Keep it under 90 characters. |

Rules:
- Store percentages as percent values (`71`, unit `%`), never fractions.
- Store money in dollars with unit `$`; the page compacts it to `$1.9M`.
- Series used by one chart share a length and the same `x` array.
- A value you could not get is left out. Never fill a gap with an estimate unless the
  note says it is an estimate and who made it.
- Demonstration data is allowed only when the user asked for it; the story then says so.

## The derive table

Arithmetic belongs to code. Put every computed number in `derive`; `chronicle build` and
`chronicle check` compute them before reading the story, in table order, so an entry can
use one computed above it. Each entry names its target path, a `fn`, the inputs as paths,
and optional `unit`, `source` and `note` copied onto the result.

```json
"derive": {
  "plan.done_now": {"fn": "last", "of": "plan.done", "unit": "pts", "source": "jira"},
  "plan.done_pct": {"fn": "share", "of": "plan.done_now", "to": "plan.scope_now", "unit": "%"},
  "plan.forecast_finish": {"fn": "burnup_finish", "done": "plan.done", "scope": "plan.scope",
                           "dates": "plan.sprint_end", "window": 6, "sprint_days": 14}
}
```

| fn | Inputs | Result |
| --- | --- | --- |
| `last` | `of` (series) | final value |
| `total` | `of` (series) | sum |
| `max`, `min` | `of` (series) | largest or smallest value |
| `mean_last` | `of`, `n` (default 6) | mean of the last n values, whole units |
| `growth_last` | `of` (cumulative series), `n` | average step over the last n steps |
| `diff` | `of`, `minus` | of minus minus |
| `ratio` | `of`, `to` | of divided by to; one decimal below 10 |
| `share` | `of`, `to` | of as a whole percent of to |
| `pct_change` | `from`, `to` | whole percent change |
| `burnup_sprints` | `done`, `scope`, `dates`, `window`, `sprint_days`, optional `growth` | sprints until done meets scope at the recent pace; `growth: 0` projects a frozen scope |
| `burnup_finish` | same | ISO date of that crossing, matching the page's burnup chart |
| `days_between`, `weeks_between` | `from`, `to` (dates) | days or whole weeks, negative when `to` is earlier |

Need a calculation that is not listed? Compute it in a short script, store the result as a
plain fact and put the method in its `note`.
