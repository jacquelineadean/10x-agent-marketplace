---
name: audit
description: Audit recent Claude Code sessions in this project for wasted tokens, apply the low-risk fixes and walk the user through medium and high-risk recommendations with evidence. Use for "why is this costing so much", "optimize my token use", "audit my sessions", context bloat, cache misses, model or effort choice, or after tokenwise reports new findings.
argument-hint: "[--days N]"
---

# /tokenwise:audit

Code reads the transcripts and computes every number. You read only the command's printed
lines and `digest.md`.

## 1. Audit
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" audit --days 14
```
It prints at most 15 lines and the digest path. Read the digest. Never open transcripts,
`findings.json` or `metrics.json`.

## 2. Low risk
Low-risk findings with "Auto-fix available" change only `.claude/settings.local.json`
(a Bash output cap or a Read deny rule for a generated file). The Stop hook applies them
unless `TOKENWISE_AUTO_APPLY=0`. Apply any left:
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" apply
```
Report each `APPLIED` line and say `tokenwise undo` reverts the last batch. Low-risk
findings without a fix (retry loops, re-reads) are habits: state them in one line each.

## 3. Medium risk
For each, give the evidence and one concrete change, then ask before doing it:
- `repeated-command`: write a script under `scripts/` or add the command to AGENTS.md.
- `retry-loop`: find the cause and record the fix in AGENTS.md.
- `subagent-model`: add `model: haiku` to that agent's definition.
- `downgrade-model`, `output-heavy`, `context-peak`, `cache-miss`, `explore-in-main`,
  `mcp-output`: habits or settings the user changes; name the command (`/model sonnet`,
  `/effort low`, `/tokenwise:handoff` then `/clear`, the Explore subagent).

## 4. High risk
`instruction-size` and `unused-mcp` change what every session loads. Show the evidence,
propose the exact edit (which sections move into which skill, which server to disable),
and make it only on an explicit yes. Make the edit as the session's last step: changing
CLAUDE.md or MCP servers mid-session rebuilds the prompt cache.

## 5. Reply
At most 12 lines: tokens at stake, what was applied, the top three recommendations with
their token estimates, and the digest path.

## Never
- Never read transcripts or raw JSON outputs into the conversation.
- Never edit CLAUDE.md, AGENTS.md, skills, agents or `.mcp.json` without a yes.
