---
description: An animation of a drawing the user already has. Checks that the diagram kind is picked over a TAD, the steps play the drawing's own ids, and the SVG builds.
tags: [full, animation]
max_turns: 80
timeout_seconds: 1800
allowed_tools: [Skill, Read, Glob, Grep, Bash, Write, Edit, TodoWrite]
expected_outcome: chronicle-runs/paging/build/animation.svg exists; animation.json has kind diagram, 3 to 6 steps, and shows the drawing's ids.
---

Animate docs/paging-path.svg for the on-call README: step through how an alert reaches the on-call engineer and then the status page. Keep my drawing; just make it play. Put the run in chronicle-runs/paging.
