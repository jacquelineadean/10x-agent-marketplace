---
type: llm
focus: { source: file, path: chronicle-runs/fare-app/facts.json }
weight: 2
---
The notes the user gave were: scope 60 tickets; tickets done (cumulative) July 18, August 31, September 42; monthly active riders July 12400, August 19800, September 27300; stations live 9 of 14; failed card taps per week 140 (first week of July) and 35 (last week of September); as-of date 2026-09-30. The budget was explicitly not available.

You are shown the facts.json file the agent wrote.

PASS if every number stored as a plain value or series is one of the numbers above (dates, month labels and years count as fine), and no budget, cost or money figure appears. Entries inside a "derive" table are formulas, not stored numbers, so ignore their results.
FAIL if any stored number is not in the notes (an invented or estimated figure), or a budget or money figure appears.
