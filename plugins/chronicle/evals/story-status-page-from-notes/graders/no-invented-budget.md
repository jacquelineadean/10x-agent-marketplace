---
type: regex
target: { source: file, path: chronicle-runs/fare-app/facts.json }
pattern: '"unit"\s*:\s*"\$"'
match: not_contains
---
