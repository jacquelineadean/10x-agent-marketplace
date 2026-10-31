---
name: prototype
description: Build a clickable, data-driven prototype of an app's screens as an HTML Artifact, with tabs, cards, lists, tables and charts fed by real facts, links between screens, desktop and phone widths, and widgets for behavior. Use for product and internal-tool concepts, on-call and admin consoles, workflow walkthroughs and design reviews that need real numbers. For dashboards of KPIs use briefing; for illustrated stories use chronicle.
---

# Prototypes from facts

A prototype is a story file with `"layout": "prototype"`: each chapter is a screen behind a
tab. A card or list row with `link` opens the screen it names, so a reviewer can click
through the flow. Every number is a fact token with its source on hover.

1. **Brief.** Ask only what the request leaves open, in one AskUserQuestion: who uses the
   app and for what task, the screens and the path between them, and the systems whose
   numbers fill them.
2. **Start.** `"${CLAUDE_PLUGIN_ROOT}/scripts/blueprint" new blueprint-runs/<slug> --layout prototype --title "App name"`.
3. **Facts.** Call `sources:gatherer` for company numbers and read `digest.md`; or put the
   user's pasted numbers in `facts.json` with their sources
   (`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/facts.md`).
4. **Write.** Read `references/prototype-format.md` and the engine's
   `${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/blocks.md`. Name screens for the
   user's task, not the data model. Use a `widget` for behavior no block has
   (`${CLAUDE_PLUGIN_ROOT}/src/chronicle_engine/references/widgets.md`).
5. **Build and look.** `check`, `build`, then `shoot`; `check` refuses a link to a screen
   that does not exist. Click through every link in the screenshots' flow before
   publishing.
6. **Publish** `build/artifact.html` with the Artifact tool after the user confirms.
