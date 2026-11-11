---
name: solution-visualizer
description: Compare several approaches to one system design question on an interactive page before building any of them, then implement the chosen one. The page has sliders for inputs such as traffic, settings per approach to change, turn off or copy into variants, scenarios to switch and save, measures against budgets, a wait the reader sits through in real time and failures out of 100 requests. Use for "which approach should we take", tradeoffs between latency, cost, failures and stale data, capacity and configuration what-ifs, options in a design review, and "implement the decision from the visualizer". For clickable app screens use prototype; for diagrams use architecture.
argument-hint: "[design question, or the path of an exported decision.json]"
---

# Solution visualizer

A run is a prototype story with one `solutions` block. The block names `solutions.json`:
the approaches, the inputs and settings a reader moves, the scenarios, and one formula per
measure and approach. Code computes every number, in the build and again on the page as a
control moves. You write the model and the words; you never do the arithmetic.

The user arrives one of two ways. With a design question, follow steps 1 to 6. With a
decision exported from the page (pasted JSON or a file), go to step 7.

1. **Brief.** Ask only what the request leaves open, in one AskUserQuestion: the question
   in one sentence, the 2 to 4 approaches (propose them when the user has none), the
   measures that decide it and their budgets (p95 latency, failures, data age, cost), the
   scenarios (a typical day, a peak, a dependency failing) and where the numbers come from.
2. **Context, for a system that exists.** Call the `blueprint:solution-scout` subagent
   with `Mode: survey`, the question and the run folder. It reads the repository on Haiku
   and writes `context.md`, at most 8 KB; read that file and no source file it cites. For
   traffic and timings from company systems call `sources:gatherer` and read `digest.md`.
   Skip this step for a design with no code yet.
3. **Start.** `"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" solutions new blueprint-runs/<slug> --title "Short name"`.
4. **Model.** Read `references/solutions-format.md`, then write `solutions.json`. Measured
   inputs go in `facts.json` with their source and enter the model as `"@path"`; an input
   with no source shows on the page as an assumption. Name the configuration key each
   setting lands in (`key`) when the scout found it. Give the measure a reader should feel
   a `feel`.
5. **Simulate and read.** `"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" solutions simulate blueprint-runs/<slug>/story.json`
   writes `solutions-results.json` and `solutions-digest.md`. Read the digest only. Before
   building, check the model against what you know: each approach misses a budget where
   you expect, each swing runs in the right direction, and no control is reported as moving
   nothing. Fix the formula, never the number, and simulate again. Prose in `story.json`
   cites results as `{{solutions.<scenario>.<approach>.<measure>}}`. Add screens with
   prototype blocks, or an `architecture` block per approach, where they help the decision.
6. **Build, look, publish.** `check`, `build`, then `shoot`, and read both screenshots.
   Publish `build/artifact.html` with the Artifact tool after the user confirms. Tell the
   user what the page does: move inputs, change settings, add a variant, press Choose, then
   "Copy the decision" and paste it back. To add or change an input, a setting, a scenario
   or an approach later, edit `solutions.json`, simulate, build and publish again.
7. **Implement the decision.** Read `references/implement.md` and follow it. It turns the
   export into `decision.md`, locates each setting in the code through the scout, and has
   you implement the chosen approach with exactly the decided settings.

Never read `build/index.html`, `solutions-results.json` or the scout's sources: the digest,
`context.md` and `decision.md` hold what you need in under 12 KB each.
