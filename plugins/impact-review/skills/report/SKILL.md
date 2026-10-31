---
name: report
description: Produce an impact review from GitHub activity for one person, a list of people, a team, an organization or an enterprise, over any timeframe (default year to date; also last month, last quarter, 30d, 1y, a calendar year or quarter, all time or a date range). Writes a metrics dashboard, a rubric-based review, highlight bullets and STAR stories into a local run folder. Use for self-evaluations, manager reviews, promotion packets, resume bullets, interview stories, team retrospectives, quarterly business reviews, organization reports or GitHub contribution metrics.
argument-hint: "[timeframe] [--scope me|user:A,B|team:ORG/SLUG|org:ORG|enterprise:SLUG] [--exclude LOGIN] [--org ORG] [--host HOST] [--repo-share] [--max-tokens N] [--rubric PATH]"
---

# /impact-review:report

The collector (Python, standard library) does every GitHub call and every calculation.
You run it, read its short output, then hand the run folder to the `impact-writer` subagent.
You never read raw API data, `metrics.json` or `digest.md` yourself.

## 1. Parse the request
- Scope (whose work), passed as `--scope`:
  - `me` (default): the token's owner.
  - `user:LOGIN` or `user:a,b,c`: named people.
  - `team:ORG/SLUG` (comma list allowed): team members, child teams included.
  - `org:ORG` (comma list allowed): organization members.
  - `enterprise:SLUG`: members of every organization in the enterprise.
  Team, org and enterprise scopes count only repositories those organizations own, unless
  the user names `--org` owners. `--exclude LOGIN` (repeatable) drops people such as bots.
  `--max-people N` (default 100) stops a run that resolves to more people.
- Timeframe, passed as `--timeframe` (default `ytd`):
  - to date: `ytd`, `qtd`, `mtd`;
  - previous whole period: `last week`, `last month`, `last quarter`, `last year`;
  - rolling, ending today: `30d`, `2w`, `1m`, `3 months`, `1q`, `1y`, `past year`, `last 2 years`;
  - calendar: `2025`, `2026-Q3`, `2026-03`;
  - all of it: `all time` (from the oldest account creation date in scope);
  - range: `2026-01-01..2026-09-30`, or `2026-01-01..` to today.
  Map the user's words to one of these forms ("this quarter" is `qtd`, "the past 12 months" is `12m`).
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
PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" <runner> -m impact_review collect --scope "<scope>" --timeframe "<timeframe>" [options]
```
Example with uv: `PYTHONPATH="${CLAUDE_PLUGIN_ROOT}/src" uv run --no-project --python 3.11 python -m impact_review collect --scope team:acme/platform --timeframe "last quarter"`.

The collector prints at most 15 lines. Read them; show the user the run folder, scope,
timeframe and counts lines.
- Exit 0: continue to step 4.
- Exit 2: the token estimate is over the cap. Show the estimate and cap lines, then ask the user
  to choose one: rerun with `--max-tokens <higher>`, accept the digest as trimmed by the collector
  (rerun is not needed; the digest already fits 12 KB), or cancel. Only on an explicit choice
  continue to step 4 with the chosen cap.
- Exit 1: show the `error:` line. A missing token message names the fix
  (`GITHUB_TOKEN`, `GH_TOKEN` or `gh auth login --hostname HOST`); an SSO message names the
  authorization step; a scope message names the missing team, organization or token scope
  (`read:org`, `read:enterprise`); a people-cap message names `--max-people` and `--exclude`. Stop.

## 4. Write the synthesis
Invoke the `impact-writer` subagent with this prompt and nothing else:
`Run folder: <run folder path>. Read digest.md and rubric.md there, then write review.md, highlights.md and stories.md into the same folder.`

Relay its reply (at most 5 lines) to the user, plus the dashboard paths:
`dashboard.md` and `dashboard.html` in the run folder.

## Never
- Never read `raw/`, `metrics.json`, `digest.md` or `budget.json` into the conversation.
- Never print the token or any `Authorization` header.
- Never commit or upload the run folder; it can hold private organization data.
