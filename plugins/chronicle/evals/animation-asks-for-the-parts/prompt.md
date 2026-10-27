---
description: An animation request with no description of the system. The skill must ask for the components or the source document instead of drawing an invented architecture.
tags: [smoke, animation]
max_turns: 12
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion]
expected_outcome: The animation skill fires, no animation is built, and the reply asks for the parts or the design doc.
---

Animate our payments architecture for the onboarding deck.
