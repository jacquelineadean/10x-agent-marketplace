---
name: handoff
description: Write a handoff file for the current task so a fresh session can continue it, then clear the context. Use when the context is large, before switching tasks, when a session feels slow or repetitive, or instead of /compact.
---

# /tokenwise:handoff

A fresh session that reads a one-page handoff costs less than `/compact`, which sends
the whole context to the model to summarize it.

## 1. Facts
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" handoff
```
It prints the handoff path. The file holds the first and latest requests, files changed,
commands run and commands that failed, all taken from the transcript.

## 2. State and next steps
Read the file. Replace the line under `## State and next steps` with at most 10 bullets
from this session: what is done, what is half done, the next step, decisions made and
why, and open questions. Use paths and names. Leave the facts above it unchanged.

## 3. Reply
Two lines: the handoff path, and this instruction for the user:
`/clear`, then send "Read <path> and continue."
