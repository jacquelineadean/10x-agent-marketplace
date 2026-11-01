---
description: A story request with no data, no sources and no connected tools. The skill must settle the brief and ask for facts instead of building a page from invented numbers.
tags: [smoke, story]
max_turns: 12
timeout_seconds: 600
allowed_tools: [Skill, Read, Glob, Grep, Bash, Write, Edit, AskUserQuestion]
expected_outcome: The story skill fires, no page is built, and the reply asks for the numbers or the sources to use.
---

Make an illustrated status page for the Atlas data-warehouse migration, for Friday's steering committee.
