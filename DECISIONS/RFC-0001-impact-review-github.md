---
id: RFC-0001
title: impact-review plugin: GitHub contribution metrics and review synthesis
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: personal review prep
support: [Jacqueline Dean]
owner: Jacqueline Dean
supersedes: []
related_rfcs: []
author: Jacqueline Dean
created: 2026-10-07
---

# RFC-0001 — impact-review plugin: GitHub contribution metrics and review synthesis

## 1. Summary
Build the first plugin in this marketplace, **impact-review**.
A local Python collector pulls one person's GitHub activity for a timeframe (default year to date), computes metrics like GitHub Insights, and writes a dashboard plus a compact digest.
A Claude subagent reads only the digest and writes a self-evaluation draft, resume bullets and interview stories.
Each run is capped at 25,000 model tokens; Claude never sees raw API data, and a run that would exceed the cap stops and asks first.

## 2. The need
**User scenario:** Jacqueline Dean prepares an end-of-year self-evaluation from a corporate GitHub Enterprise account. Today that means hours in repo pages, pull request lists and Insights tabs, and the result has few numbers. The same material is reused later for a resume and interview answers.
**Done means:** one command in Claude Code produces, in a local run folder, a metrics dashboard (Markdown and HTML), a self-evaluation draft, resume bullets and interview stories. Every number in the written files matches a value in `metrics.json`.

## 3. Interview record
| # | Question | Answer | Effect |
| --- | --- | --- | --- |
| 1 | Who owns this repo and its plugins? | Jacqueline Dean, owner | Confirmed |
| 2 | Who uses the extensions? | Jacqueline Dean plus teammates | Confirmed |
| 3 | Packaging format? | Claude Code marketplace: one repo, many plugins | Confirmed |
| 4 | Which GitHub host? | Support any host: github.com, Enterprise Cloud, Enterprise Server, ghe.com | Confirmed |
| 5 | How should data be pulled to keep tokens lowest? | Local script calls GitHub APIs and writes a compact summary; Claude reads only that | Confirmed |
| 6 | Collector language? | Python with uv | Confirmed |
| 7 | Where may reports with corporate data be stored? | Local only; never committed or sent anywhere | Confirmed |
| 8 | Who approves changes? | Jacqueline Dean alone | Confirmed |
| 9 | Plugin name? | impact-review; phase 2 sources join the same plugin | Confirmed |
| 10 | Code structure? | Command-line tool layout (core, connectors, entrypoints, config) | Confirmed |
| 11 | Default timeframe? | Year to date; last N days and custom dates also supported | Confirmed |
| 12 | Which written outputs? | Self-evaluation draft, resume bullets, interview stories, metrics dashboard | Confirmed |
| 13 | Original request: other sources (Claude, Cursor, Datadog, ServiceNow, PagerDuty, Jira, Confluence) and a cross-source dashboard | Next phase | Out of scope |
| 14 | Which rubric should the self-evaluation follow? | Generic five-area engineering rubric in a file the user can replace | Confirmed |
| 15 | Default run folder location? | `~/impact-review-runs/` | Confirmed |
| 16 | Which repos count with no org filter? | Every repo the token sees; `--org` narrows | Confirmed |
| 17 | Lines of code in written outputs? | Everywhere: dashboard, digest, self-evaluation, resume, stories | Confirmed |
| 18 | Does the read-back match what you want? | Add a maximum token usage so one turn cannot burn through tokens | Confirmed (see 4.8) |
| 19 | Where did the request come from? | Personal review prep | Confirmed |
| 20 | Who supports the plugin after release? | Jacqueline Dean | Confirmed |
| 21 | Have you read PROJECT.md and ARCHITECTURE.md? | Not yet read; both stay unconfirmed | Doc update |
| 22 | Maximum model token budget per run? | 25,000 tokens | Confirmed |
| 23 | What happens when a run would exceed the cap? | Stop before writing and ask the user | Confirmed |
| 24 | Which model writes the synthesis? | Sonnet | Confirmed |
| 25 | With the token cap, stop-and-ask and Sonnet writer added, is the proposal final? | Yes, that's it | Confirmed |

### Read-back
- **Confirmed:** one plugin, impact-review, in a Claude Code marketplace. A standard-library Python collector does all GitHub calls and math for any GitHub host. Claude reads only a 12 KB digest through a subagent. Outputs: dashboard (Markdown and HTML), self-evaluation on a swappable generic rubric, resume bullets, interview stories, with lines of code allowed everywhere. Default timeframe year to date; scope every repo the token sees; run folders in `~/impact-review-runs/`, never committed. Jacqueline Dean owns, approves and supports it. Each run is capped at 25,000 model tokens; over the cap it stops and asks. A Sonnet subagent with 6 turns and two tools writes the synthesis.
- **Tensions:** the groundwork rule names python-dotenv for `.env`; the Constitution bans runtime dependencies without an RFC. This RFC resolves it with a standard-library reader in `config/` (4.7).
- **Open decisions:** None. The user confirmed this read-back on 2026-10-07.
- **Docs to update after approval:** ARCHITECTURE.md gains the run folder path and the writer subagent; `.gitignore` gains Python caches; `mypy.ini` and `pyproject.toml` gain the plugin source path.

## 4. Proposal

### 4.1 What the user runs
- `/impact-review:report [timeframe] [--org ORG] [--host HOST]` in Claude Code. Timeframe forms: `ytd` (default), `last 365d`, `2026-01-01..2026-09-30`.
- The same collector runs without Claude: `python -m impact_review collect --since … --until …`. This path costs zero model tokens.

### 4.2 Plugin contents (`plugins/impact-review/`)
- `.claude-plugin/plugin.json`, `README.md`.
- `skills/report/SKILL.md`: parses the request, runs the collector through `${CLAUDE_PLUGIN_ROOT}`, then hands the run folder to the subagent.
- `agents/impact-writer.md`: a subagent that reads `digest.md` and the rubric only, writes the three synthesis files, and returns a five-line summary. Raw data never enters the main conversation.
- `src/impact_review/`: the collector, standard library only.

### 4.3 Data collected (all read-only, viewer's own data only)
| Data | Source | Used for |
| --- | --- | --- |
| Profile and login | GraphQL `viewer` | header, attribution |
| Totals, daily calendar, per-repo counts | GraphQL `contributionsCollection`, one call per year of range | volume, consistency, repo breakdown |
| Pull requests opened: size, state, merge time, first review time, labels, reviewers | `pullRequestContributions`, 100 per page | delivery, flow, size, themes |
| Reviews given: state, comment count, PR author and repo | `pullRequestReviewContributions` | collaboration |
| Issues opened | `issueContributions` | ownership |
| Commits on default branches: date, headline, lines | repo `history(author:)` per contributed repo | code volume, cadence |
| Repo share of commits and lines (optional flag) | REST `stats/contributors` | Insights-style share per repo |

Ranges longer than one year are split, because GitHub limits each contribution query to one year.
Every response is cached in the run folder; reruns reuse the cache unless `--refresh` is set.
Scope: every repo the token can see, narrowed by repeatable `--org ORG`.
Run folder: `~/impact-review-runs/<host>/<login>/<since>_<until>/`, overridable with `--out DIR`.

### 4.4 Metrics computed in `core/` (no model involved)
- **Volume:** commits, PRs opened, merged, closed unmerged; reviews by outcome; review comments; issues; repos and orgs touched; languages.
- **Code:** lines added and deleted on merged PRs, files changed, PR size bands (under 10, 10 to 99, 100 to 499, 500 to 999, 1,000+ lines).
- **Flow:** median and 75th percentile time to merge; median time to first review; PRs merged per week.
- **Collaboration:** distinct authors reviewed, distinct reviewers of own PRs, reviews per PR opened, cross-repo reach.
- **Consistency:** active days, longest streak, share of active weeks, activity by weekday and month.
- **Repo share:** own share of commits and lines per repo (optional).
- **Themes:** PRs grouped as feature, fix, refactor, test, docs, CI/infra, performance, security, dependencies, using title prefixes, labels and keywords.
- **Highlights:** top 15 PRs ranked by size, review discussion and reach; top repos.

### 4.5 Outputs in the run folder
| File | Written by | Read by Claude? |
| --- | --- | --- |
| `raw/*.json` | collector | never |
| `metrics.json` (with `schema_version`) | collector | never in full |
| `dashboard.md`, `dashboard.html` (offline, inline SVG charts, no external scripts) | collector | no |
| `digest.md` (hard cap 12 KB, about 3,000 tokens) | collector | yes |
| `self-evaluation.md`, `resume-bullets.md`, `interview-stories.md` | subagent | written |

### 4.6 Synthesis rules
- Every number cites a `metrics.json` key, for example `(prs.merged = 142)`.
- Business outcomes GitHub cannot know, such as revenue or latency gains, appear as `[ADD OUTCOME: …]` for the user to fill.
- The self-evaluation follows `rubric.md`. The default covers five areas: delivery and impact, technical quality, collaboration and review, ownership and reliability, growth and leadership. `--rubric PATH` swaps in the company framework.
- Resume: 8 to 12 bullets, each verb, scope, number. Stories: 4 to 6, each situation, task, action, result, built from top PRs and themes.

### 4.7 Auth and hosts
- Token from `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token --hostname HOST`. Scopes: `repo`, `read:org`, `read:user`.
- API base derived from host: `api.github.com`; `HOST/api/graphql` and `HOST/api/v3` for Enterprise Server; `api.SUBDOMAIN.ghe.com` for data residency.
- `.env` support: a ten-line standard-library reader in `config/`, which never overrides variables already set. This keeps zero runtime dependencies in place of python-dotenv.

### 4.8 Token budget (hard cap 25,000 model tokens per run)
- `--max-tokens N` sets the cap; the default is 25,000.
- Before any writing, the collector estimates the run's model tokens and saves `budget.json`. Inputs count as bytes divided by 4, rounded up.
- The estimate has five parts: digest (at most 3,000), rubric and writer instructions (about 2,000), fixed system overhead (5,000), output allowance (6,000), main conversation (3,000). A typical run totals about 19,000.
- Output caps: self-evaluation at most 900 words; at most 12 resume bullets; at most 6 stories of at most 180 words each.
- Over the cap, the skill stops before the writer starts. It shows the estimate and the cap, then asks: trim the digest to fit, raise the cap for this run, or cancel.
- The writer subagent runs on Sonnet with only the Read and Write tools and at most 6 turns. It reads `digest.md` and `rubric.md` only, and returns a summary of at most 5 lines.
- The collector prints at most 15 lines to the conversation; the skill never prints the digest.
- Limit: plugins cannot set a hard per-turn token switch in Claude Code. The cap holds through sizes known before the run, the turn limit, the tool limit and the output caps.

## 5. Alternatives considered
- **GitHub MCP server as the data path.** Rejected: each tool result lands in Claude's context as raw JSON. A year with 300 PRs and 600 reviews would cost several hundred thousand tokens, against under 25,000 here. MCP also cannot compute medians or streaks without Claude doing the math.
- **`gh` CLI shell script.** Rejected: hard to test, weak at aggregation, and `gh` may be missing on locked-down laptops.
- **Third-party Python packages (PyGithub, httpx).** Rejected for runtime: corporate laptops often block PyPI; the standard library covers HTTP and JSON.
- **Claude writes the dashboard.** Rejected: charts from Python cost zero tokens and give the same result every run.

## 6. Risks and objections
- **Private and SSO-protected contributions:** a token not authorized for the org's single sign-on sees only counts. The collector detects the SSO error and prints the authorization step.
- **Commits off the default branch are not counted by GitHub.** Squash-merged PR work still counts through PR metrics. The digest states this limit.
- **Old Enterprise Server versions may lack fields.** The collector records which metrics it skipped in `metrics.json.warnings`.
- **Contributor statistics return HTTP 202 while GitHub computes them.** The collector retries 3 times, then skips repo share for that repo with a warning.
- **Vanity metrics:** lines of code can mislead reviewers. The user chose to show them everywhere; the writer always pairs a line count with PR or review counts.
- **Python on corporate laptops:** the skill runs the collector with `uv run --no-project`, else `python3` 3.11+. If neither exists it stops with install steps.
- **Groundwork rule tension:** the standard says load `.env` with python-dotenv; the Constitution bans runtime dependencies without an RFC. This RFC chooses the standard-library reader (4.7).

## 7. Impact
**Repos touched:** 10x-agent-marketplace only. Relationship: independent, the first feature.
**Constitution check:** principle 1 (collector computes, Claude reads the digest); 2 (numbers cite `metrics.json`); 3 (run folder local, no outside calls but GitHub); 4 (GraphQL queries and REST GETs only); 5 (own folder and version).
**Cost / performance / security notes:** about 19,000 model tokens per run, hard cap 25,000 (4.8). A heavy year needs roughly 50 to 300 API calls, well under the 5,000-point hourly GraphQL limit. The token is never logged.

## 8. Cross-repo contract (only if classification is `api`)
N/A, internal.

## 9. Out of scope
- Phase 2 sources: Claude, Cursor, Datadog, ServiceNow, PagerDuty, Jira, Confluence, and cross-source correlation.
- Hosted or shared dashboards; any upload of run data.
- Reporting on another person's activity; the collector reads the token owner only.
- Writing anything back to GitHub.

## 10. Open questions
