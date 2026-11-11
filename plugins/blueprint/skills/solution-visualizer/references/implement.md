# Implement the decision

The page's "Copy the decision" gives JSON: the chosen variant with its setting values, the
variants compared with it, the inputs as they stood and the scenarios the reader saved.

1. **Save it.** Write the pasted JSON to `blueprint-runs/<slug>/decision.json` unchanged.
2. **Check it against the model.**
   `"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" solutions decide blueprint-runs/<slug>/story.json --decision blueprint-runs/<slug>/decision.json`
   refuses a value the solutions file cannot hold and writes `decision.md` beside the JSON.
   On a refusal, the page and the file differ: rebuild, publish, and ask for a new export.
3. **Read `decision.md`** and nothing else from the run. It holds the chosen approach, each
   setting with its decided and default value and its key, the model's numbers in every
   scenario, one acceptance check per budget and scenario, and the assumptions to verify.
4. **Stop when the choice misses a budget.** If `decision.md` says checks are outside their
   budget, tell the user which ones and ask whether to go on, in one AskUserQuestion.
5. **Locate.** Call the `blueprint:solution-scout` subagent with `Mode: locate`, the path
   of `decision.md` and the run folder. It writes `locate.md`, at most 6 KB: where each key
   is defined and read, its value today, the files on the chosen approach's path and the
   tests that cover them. A setting marked "to locate" with no match is new configuration.
6. **Plan, then confirm.** State the files to change, each setting's old and new value, and
   how each acceptance check will be verified. Ask the user to confirm before editing.
7. **Implement** the chosen approach in the user's code, following the repository's own
   rules. Set every setting to exactly the decided value, including the ones turned off.
   Put each value in the key `decision.md` names; never hard-code one where a key exists.
8. **Verify.** Turn each acceptance check into a test, a benchmark or a named dashboard
   query. Run the ones that run locally. The model's numbers are expectations, never
   evidence: report a check as passed only with a measurement.
9. **Report** in four parts: what changed, each setting with its value and file, each
   acceptance check as passed, failed or not measurable here, and the assumptions from
   `decision.md` still unverified.

When a measurement contradicts the model, change the formula or the input in
`solutions.json`, simulate and build again, and tell the user the page moved.
