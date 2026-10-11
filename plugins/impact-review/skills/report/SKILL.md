---
name: report
description: Produce an impact review from the user's own GitHub activity for a timeframe (default year to date): metrics dashboard, self-evaluation draft, resume bullets and interview stories in a local run folder. Use when the user asks for a performance review draft, self-evaluation, resume bullets, interview stories or GitHub contribution metrics.
argument-hint: "[ytd | last 365d | 2026-01-01..2026-09-30] [--org ORG] [--host HOST] [--repo-share] [--max-tokens N] [--rubric PATH]"
---

# /impact-review:report

The collector (Python, standard library) does every GitHub call and every calculation.
You run it, read its short output, then hand the run folder to the `impact-writer` subagent.
You never read raw API data, `metrics.json` or `digest.md` yourself.

## 1. Parse the request
- Timeframe: `ytd` (default), `last 365d`, or `2026-01-01..2026-09-30`.
- Options pass through unchanged: `--org ORG` (repeatable), `--host HOST`, `--repo-share`,
  `--max-tokens N` (default 25000), `--rubric PATH`, `--out DIR`, `--refresh`.
- Host default: `github.com`, or `IMPACT_REVIEW_HOST` in the environment or `.env`.

## 2. Pick a Python runner
Run in Bash, first that works:
1. `uv run --no-project --python 3.11 python --version`
2. `python3 --version` (needs 3.11 or newer)

If neither works, stop and tell the user to install Python 3.11+ or uv (`https://docs.astral.sh/uv/`). Do not continue.

## 3. Run the collector
```bash
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" <runner> -m impact_review collect --timeframe "<timeframe>" [options]
```
Example with uv: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" uv run --no-project --python 3.11 python -m impact_review collect --timeframe ytd`.

The collector prints at most 15 lines. Read them; show the user the run folder line and the counts line.
- Exit 0: continue to step 4.
- Exit 2: the token estimate is over the cap. Show the estimate and cap lines, then ask the user
  to choose one: rerun with `--max-tokens <higher>`, accept the digest as trimmed by the collector
  (rerun is not needed; the digest already fits 12 KB), or cancel. Only on an explicit choice
  continue to step 4 with the chosen cap.
- Exit 1: show the `error:` line. A missing token message names the fix
  (`GITHUB_TOKEN`, `GH_TOKEN` or `gh auth login --hostname HOST`); an SSO message names the
  authorization step. Stop.

## 4. Write the synthesis
Invoke the `impact-writer` subagent with this prompt and nothing else:
`Run folder: <run folder path>. Read digest.md and rubric.md there, then write self-evaluation.md, resume-bullets.md and interview-stories.md into the same folder.`

Relay its reply (at most 5 lines) to the user, plus the dashboard paths:
`dashboard.md` and `dashboard.html` in the run folder.

## Never
- Never read `raw/`, `metrics.json`, `digest.md` or `budget.json` into the conversation.
- Never print the token or any `Authorization` header.
- Never commit or upload the run folder; it holds corporate data.
