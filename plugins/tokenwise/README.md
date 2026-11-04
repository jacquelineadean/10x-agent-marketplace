# tokenwise

Token optimization for Claude Code. tokenwise reads your session transcripts, finds where
tokens went to waste, applies the fixes that are safe and reversible, and recommends the
rest with evidence. Hooks guard against retry loops and save handoff facts before
compaction. All analysis is deterministic Python: no model call reads a transcript.

Read-only against transcripts. Standard-library Python. Data stays on your machine.

## Install
```
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install tokenwise@10x-agent-marketplace
```
Needs Python 3.11+ or `uv`. No Python packages are downloaded.

## What it does
| Part | When | Cost in model tokens |
| --- | --- | --- |
| Stop hook | after each turn: audits that session, applies new low-risk fixes, shows a one-line note to you | none; the note is a `systemMessage` |
| Loop guard (PostToolUse, PostToolUseFailure on Bash) | the third failure in a row of the same command | one short reminder to Claude |
| PreCompact hook | before `/compact` or auto-compaction | none; writes handoff facts to a file |
| `/tokenwise:audit` | on demand | the digest, capped at 12 KB |
| `/tokenwise:handoff` | when switching tasks or the context is large | the handoff file, about 1 KB |

## Rules
Costs are weighted in input-token equivalents using Anthropic's price multiples: 5-minute
cache write 1.25x, 1-hour write 2x, output 5x, cache read 0.05x on the 5.5 models and 0.1x
on older ones. Each finding carries an estimate of tokens at stake.

| Rule | Tier | Fires when | Action |
| --- | --- | --- | --- |
| `bash-output-limit` | low | 5+ Bash results of 20,000+ characters in a session | auto: `env.BASH_MAX_OUTPUT_LENGTH=15000` |
| `deny-generated-read` | low | a lockfile, minified, map or build file read for 10,000+ characters | auto: `permissions.deny` `Read(./path)` |
| `retry-loop` | low | the same command failed 3+ times | record the cause in AGENTS.md; the loop guard warns live |
| `reread` | low | one file read 4+ times in a session | read once with line ranges |
| `context-peak` | medium | context passed 150,000 tokens | `/tokenwise:handoff`, then `/clear` |
| `cache-miss` | medium | under 70% of context from cache over 20+ responses | keep model, CLAUDE.md and MCP fixed in a session |
| `explore-in-main` | medium | 30+ Read, Grep and Glob calls and no subagent | send searches to the Explore subagent |
| `downgrade-model` | medium | an Opus or Fable session with no file changes, 5 to 40 responses | `/model sonnet` or `/effort low` |
| `subagent-model` | medium | a subagent on a large model that only reads, 5 to 40 responses | `model: haiku` in its definition |
| `output-heavy` | medium | 20,000+ output tokens and over half the weighted cost | terse output style, edits over rewrites |
| `mcp-output` | medium | MCP results of 40,000+ characters | narrower queries, a subagent, or `MAX_MCP_OUTPUT_TOKENS` |
| `repeated-command` | medium | the same non-trivial command in 3+ sessions | a script, a skill or the AGENTS.md command list |
| `instruction-size` | high | CLAUDE.md, AGENTS.md and the user CLAUDE.md over 12,000 bytes | move rare procedures into skills |
| `unused-mcp` | high | a `.mcp.json` server with no calls in 3+ sessions | disable it |

Low-risk fixes write only `.claude/settings.local.json` in the project, Claude Code's
personal, git-ignored settings file. Every change is logged with the value it replaced.
`tokenwise undo` restores the last batch, and an undone fix is never applied again.
Medium and high-risk changes are recommendations; the audit skill makes them only after
you say yes. High-risk edits wait for the end of a session because they rebuild the cache.

## Commands
```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" audit [--days 14] [--transcript FILE] [--apply]
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" apply
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" undo
"${CLAUDE_PLUGIN_ROOT}/scripts/tokenwise" handoff [--transcript FILE]
```
`--project DIR` before the command picks another project (default: the current folder).

## Settings
| Variable | Default | Meaning |
| --- | --- | --- |
| `TOKENWISE_AUTO_APPLY` | `1` | `0` stops the Stop hook from applying fixes; it still reports |
| `TOKENWISE_RUNS` | `~/tokenwise-runs` | data folder root; one subfolder per project |
| `CLAUDE_CONFIG_DIR` | `~/.claude` | where Claude Code keeps `projects/` transcripts |

The data folder holds `digest.md`, `findings.json`, `metrics.json`, `applied.json`,
`handoffs/` and per-session hook state. Never commit it.

## Manual test
1. Install the plugin and work for a few turns in a project.
2. Run `/tokenwise:audit`. Expect at most 15 lines from the command and a digest path.
3. Run a failing command three times, such as `false`. Expect a tokenwise reminder after the third.
4. Run `/compact`. Expect a note naming a handoff file under `~/tokenwise-runs/`.
5. Run `tokenwise undo` after any applied fix and check `.claude/settings.local.json`.

## Limits
Claude Code does not document its transcript format. The parser follows the lines it
writes today (one line per content block, usage repeated per line) and skips lines it
cannot read. Subagent transcripts are read from `<session>/subagents/`.
