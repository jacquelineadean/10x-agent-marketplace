# Spec 003: blueprint solution visualizer

Source: the owner's request of 11 Nov 2026. No RFC: the change adds a skill, a block, a command and an agent to
blueprint, with no new plugin, no runtime dependency and no constitution change.
Each acceptance criterion names the test that checks it or a manual check.

## What it adds
`/blueprint:solution-visualizer` extends the prototype skill. A software engineer or solution architect compares 2 to
6 approaches to one system design question on an interactive page, changes inputs and settings, simulates scenarios,
feels a tradeoff such as latency, and then implements the chosen approach with the chosen settings.

## Design decisions
The component choices follow the Claude Code plugin documentation (`code.claude.com/docs/en/skills`, `sub-agents`,
`hooks` and `plugins/components`, read on 11 Nov 2026).

- **One skill, two entry points.** The docs keep a reusable workflow in a skill, under 500 lines, with reference
  files loaded when needed. `SKILL.md` is 49 lines; `references/solutions-format.md` loads when Claude writes the
  model and `references/implement.md` only when a decision comes back. One description covers both the design
  question and "implement the decision", so one skill triggers for the whole loop.
- **A script computes.** Constitution principle 1: formulas are data Claude writes; `blueprint solutions` and the
  page compute. The command is part of the existing `scripts/blueprint`, called through `${CLAUDE_PLUGIN_ROOT}`.
- **Formulas are arithmetic text read by the standard `ast` module.** No runtime dependency and no `eval`. The
  reader accepts numbers, names, `+ - * / % **`, comparisons, `and`, `or`, `not`, `a if c else b` and 11 functions,
  and returns a tree of nested lists.
- **One tree, two walkers, one comparison.** The build walks the tree in Python; the page walks the same tree in
  JavaScript as a control moves. Both use floored modulo, round halves up, compute only the taken branch and refuse a
  step that is not finite. The build ships its results; the page compares its first numbers with them and says so
  when they differ.
- **Every number has a source.** An input names a story source or shows as an assumption. `simulate` writes results
  as facts with source `model`, so prose cites them through tokens. `check` stops a build whose stored results
  differ from what the file computes.
- **Add, enable, disable, update.** A reader updates inputs and settings with sliders, switches and choices; turns a
  setting with `off` on and off; takes a variant in and out of the comparison; adds a variant (a copy of an
  approach's settings, up to 6 columns) and a scenario (the inputs as they stand). Adding a control or an approach
  is an edit to `solutions.json` and a rebuild.
- **Feel.** A measure with `feel: wait` plays its value in real time, one bar per compared variant, and replays
  0.4 s after a control comes to rest. `feel: failures` marks the failing share of 100 requests. A wait longer than
  15 s stops at 15 s and still states its whole length. Reduced motion shows the results with no bar running.
- **The decision is a file.** The page exports JSON; `solutions decide` checks it against the solutions file and
  writes `decision.md` with the settings, their keys, the model's numbers per scenario and one acceptance check per
  budget and scenario. Claude implements from that file after the user confirms a plan.
- **Subagent models by task.** The docs route search to "faster, lower-cost models like Haiku" and give subagents a
  `tools` allowlist.

  | Task | Runs in | Model | Why |
  | --- | --- | --- | --- |
  | Find the request's path, settings, limits and stated numbers in a repository | `blueprint:solution-scout`, tools Read, Grep, Glob, Write, at most 30 turns | Haiku | Search and copy with a file and line; no judgment on the design. File reads stay out of the session. |
  | Read traffic and timings from company systems | `sources:gatherer` (exists) | Sonnet | Query writing against nine systems. |
  | Write the model, read the digest, implement the decision | the session | the user's model | Iterative work with the user; the docs keep back-and-forth in the main conversation. |

- **No hook, no MCP server.** The docs say plugin hooks fire from session load, in every session with the plugin
  enabled; this workflow starts when a user asks. The page is static and reads nothing after it loads.
- **Token use.** Claude reads `solutions-digest.md` (12 KB cap), `context.md` (8 KB), `locate.md` (6 KB) and
  `decision.md`, never the built page, the results file or the repository files the scout cites.

## Acceptance criteria
| ID | Criterion | Check |
| --- | --- | --- |
| AC-1 | A formula accepts arithmetic only; a call, an attribute, a string or a chained comparison is refused with what to use | `test_blueprint_solutions.py::test_a_formula_that_is_not_arithmetic_is_refused` |
| AC-2 | A formula computes with floored modulo, halves rounded up and only the taken branch; a division by zero or a value that is not finite raises | `::test_a_formula_computes_by_the_rules_the_page_shares`, `::test_a_value_that_is_not_finite_raises` |
| AC-3 | The page's script holds every operation the reader emits and computes the build's numbers for each of them in Chromium | `::test_the_page_script_has_every_operation_the_reader_emits`, `::test_the_page_script_agrees_on_every_operation` |
| AC-4 | `check` refuses a solutions file with an unknown name, a circle, a missing formula, a value outside its range, an unknown fact, or a value that is not finite in a scenario or at a control's min or max; each error says what to change | `::test_a_solutions_file_error_says_what_to_change` |
| AC-5 | A control that moves no measure and a number typed into a label are warnings; the example has none | `::test_a_control_that_moves_nothing_and_a_typed_number_are_warnings` |
| AC-6 | An approach reads its own settings and the shared formulas it needs, in order; a setting turned off takes its `off` value | `::test_an_approach_reads_only_its_own_settings_and_shared_formulas`, `::test_a_setting_turned_off_takes_its_off_value` |
| AC-7 | `solutions simulate` writes results as facts and a digest under 12 KB with results per scenario, budget misses, the largest swings and inputs with no source | `::test_the_example_computes_what_its_formulas_say`, `::test_the_digest_gives_results_misses_swings_and_assumptions_under_the_cap` |
| AC-8 | A build stops when stored results are older than the file, and when a story holds two solutions blocks | `::test_results_older_than_the_file_stop_the_build`, `::test_a_second_solutions_block_is_an_error` |
| AC-9 | `solutions new` starts a run that simulates and builds; a second `new` in the folder is refused | `::test_new_starts_a_run_that_builds` |
| AC-10 | The example checks with 0 warnings and builds a page with a static results table, the trees, the build's results and prose that cites results through tokens; its stored results and digest are current | `::test_the_example_checks_clean_and_builds_the_page`, `::test_the_examples_stored_results_and_digest_are_current` |
| AC-11 | On the page a reader switches scenario, moves an input, turns a setting off, adds a variant, chooses it and copies a decision that `decide` accepts; the numbers shown equal the build's | `::test_the_page_script_computes_the_builds_numbers`; browser check M-1 |
| AC-12 | `solutions decide` writes `decision.md` with decided and default settings, keys, expectations per scenario including saved ones, acceptance checks and assumptions; it counts checks outside their budget | `::test_a_decision_becomes_settings_expectations_and_checks`, `::test_a_decision_with_a_setting_off_and_new_inputs_reports_the_misses` |
| AC-13 | A decision that names an unknown variant, approach or setting, or a value a control cannot hold, is refused | `::test_a_decision_the_file_cannot_hold_is_refused`, `::test_decide_writes_decision_md_and_refuses_a_bad_export` |
| AC-14 | The scout runs on Haiku with Read, Grep, Glob and Write only; the skill is under 100 lines and every reference it names exists | `::test_the_scout_runs_on_haiku_without_shell_or_edit_and_the_skill_names_its_parts` |
| AC-15 | The wait replays after a slider comes to rest, saved scenarios and added variants appear in the scenario table, and the page fits 390 pixels with no sideways scroll | browser check M-1 |
| AC-16 | The four quality gates and `claude plugin validate .` pass; no `version` field changes | CI |
| AC-17 | The skill runs end to end in Claude Code, from a design question to `decision.md` | manual check M-2 |

## Manual checks
- **M-1.** Build `examples/catalog-solutions` and drive it in Chromium at 1320 and 390 pixels: pick "Sale peak", set
  page views to 1,000, save the inputs as a scenario, turn the cache's timeout off and its stale-serving on, add a
  variant and rename it, take the first approach out of the comparison, switch the scenario table's measure, press
  "Open the product page", move the slider again and watch the bars replay, choose the variant and copy the
  decision. Record script errors (none allowed), the count of cards and lanes, and the sideways overflow at 390
  pixels (0).
- **M-2.** `claude --plugin-dir plugins/blueprint`, then `/blueprint:solution-visualizer` with a design question in
  a repository: confirm the scout writes `context.md`, the digest matches the page, and a pasted decision produces
  `decision.md` and a plan to confirm. This needs a Claude Code session and cannot run in the build container.

## Out of scope
- Measured data: the page computes a model. `implement.md` has Claude report a check as passed only with a
  measurement.
- Saving a reader's state between visits, and sharing it between readers.
- Feel kinds beyond a wait and failures.
- Monte Carlo or time-stepped simulation: a formula gives one value per set of inputs.
