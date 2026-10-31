# impact-review

Turns GitHub activity into metrics, an offline dashboard, a rubric-based review, highlight
bullets and STAR stories. The scope is one person, a list of people, a team, an organization
or an enterprise; the timeframe is any period from last week to all time (default year to
date). A standard-library Python collector makes every API call and every calculation;
Claude reads only a 12 KB digest.

| Scope | Typical use | `review.md` | `highlights.md` | `stories.md` |
| --- | --- | --- | --- | --- |
| one person (`me`, `user:LOGIN`) | self-evaluation, manager review draft, promotion packet, job search | review draft in first person | resume bullets | interview stories |
| several people, team, org, enterprise | retrospective, quarterly business review, all-hands, org report | impact report in third person | update or slide bullets | case studies |

Read-only against GitHub. Local only: run folders never leave the machine.

## Install
```
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install impact-review@10x-agent-marketplace
```
Needs Python 3.11+ or `uv` on the machine. No Python packages are downloaded.

## Token
The collector looks for `GITHUB_TOKEN`, then `GH_TOKEN`, then `gh auth token --hostname HOST`.
A `.env` file in the working directory is read too; it never overrides a variable already set.

Required token scopes: `repo`, `read:org`, `read:user`; `read:enterprise` too for
`--scope enterprise:SLUG`. Enterprise organizations with single sign-on need the token
authorized for SSO; the collector names the organization and the step when GitHub refuses.
GitHub shows another person's contributions only in repositories the token can read.

## Use
```
/impact-review:report                                   # me, year to date, github.com
/impact-review:report last quarter --scope team:acme/platform
/impact-review:report 1y --scope org:acme --exclude dependabot-bot
/impact-review:report all time --scope user:alice,bob
/impact-review:report 2026-Q3 --scope enterprise:acme-corp --max-people 400
/impact-review:report 2026-01-01..2026-09-30 --host ghe.corp.example --repo-share
```
The skill runs the collector, shows at most 15 lines, then a Sonnet subagent (`impact-writer`)
reads `digest.md` and `rubric.md` and writes the three synthesis files.

Without Claude (zero model tokens):
```
PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --scope me --timeframe ytd
```

### Scopes (`--scope`)
| Form | People | Repositories counted (unless `--org` is given) |
| --- | --- | --- |
| `me` (default) | the token's owner | any owner |
| `user:LOGIN` or `user:a,b,c` | those accounts | any owner |
| `team:ORG/SLUG` (comma list allowed) | team members, child teams included | owned by ORG |
| `org:ORG` (comma list allowed) | organization members | owned by ORG |
| `enterprise:SLUG` | members of every organization in the enterprise | owned by those organizations |

`--exclude LOGIN` (repeatable) drops people. `--max-people N` (default 100) stops a run that
resolves to more people, before any contribution query. Each person costs about five GraphQL
queries per year of timeframe plus one per repository with commits.

### Timeframes (`--timeframe`)
| Form | Range |
| --- | --- |
| `ytd` (default), `qtd`, `mtd`; `this year`, `this quarter`, `this month` | start of the period to today |
| `last week`, `last month`, `last quarter`, `last year` | the previous whole calendar period |
| `30d`, `2w`, `1m`, `3 months`, `6mo`, `1q`, `1y`, `past year`, `last 2 years` | rolling window ending today |
| `2025`, `2026-Q3`, `2026-03` | that calendar period, ending today at the latest |
| `all time` (also `all`, `lifetime`) | from the oldest account creation date in scope to today |
| `2026-01-01..2026-09-30`, `2026-01-01..` | inclusive range; an open end means today |

`--since DATE --until DATE` overrides `--timeframe`. Ranges over a year are fetched in
one-year chunks, GitHub's contributionsCollection limit.

### Other flags
`--org` (repeatable), `--host`, `--out`, `--refresh`, `--repo-share`, `--max-tokens` (default
25000), `--rubric` (default `rubric-individual.md` for one person, `rubric-group.md` otherwise).
Exit codes: 0 done, 1 error (message on stderr), 2 token estimate over the cap.

Hosts: `github.com` (also Enterprise Cloud), `HOST` for Enterprise Server
(`https://HOST/api/graphql`, `https://HOST/api/v3`), `SUB.ghe.com` for data residency
(`https://api.SUB.ghe.com`).

## Run folder
Default `~/impact-review-runs/<host>/<scope>/<since>_<until>/`, where `<scope>` is the login
for one person, else `team-ORG-SLUG`, `org-ORG`, `enterprise-SLUG` or `users-a+b` (hashed
when long). `IMPACT_REVIEW_RUNS` or `--out` change it. Never commit it.

| File | Written by | Claude reads it? |
| --- | --- | --- |
| `raw/*.json` | collector (cache; a rerun makes no repeat API calls) | never |
| `metrics.json` | collector, `schema_version` 2 | never in full |
| `dashboard.md`, `dashboard.html` | collector; HTML is offline with inline SVG, no scripts | no |
| `digest.md` | collector, at most 12,000 bytes | yes, the only input |
| `budget.json` | collector, token estimate against the cap | no |
| `rubric.md` | copied from `--rubric` or the default individual or group rubric | yes |
| `review.md`, `highlights.md`, `stories.md` | impact-writer | written |

### metrics.json shape (schema_version 2)
Top-level keys: `schema_version`, `generated_at`, `host`, `scope`, `timeframe`, `volume`,
`code`, `flow`, `collaboration`, `consistency`, `themes`, `repo_share`, `highlights`, `people`,
`limits`, `warnings`. Every number in the digest carries its key, for example `(volume.prs_merged)`, and
the writer cites that key next to the number.

- `scope`: kind, targets, label, individual, people, orgs.
- `volume`: people, active_people, commits, prs_opened, prs_merged, prs_closed_unmerged, prs_open, reviews and
  outcomes, review_comments, issues_opened, repos_touched, orgs_touched, languages,
  restricted_contributions.
- `code`: lines_added, lines_deleted, lines_changed, files_changed, median_pr_lines, size_bands
  (under_10, 10_to_99, 100_to_499, 500_to_999, 1000_plus), commit_lines_added, commit_lines_deleted.
- `flow`: merge_hours_median, merge_hours_p75, first_review_hours_median, prs_with_review,
  prs_merged_per_week, prs_merged_per_person_per_week, weeks.
- `collaboration`: authors_reviewed, authors_reviewed_outside_scope, reviewers_of_own_prs,
  reviewers_outside_scope, reviews_per_pr_opened, reviews_inside_scope, reviews_outside_scope,
  repos_reviewed_in, repos_reviewed_only, cross_repo_reach. Self-reviews never count.
- `consistency`: contributions, active_days, days_in_timeframe, longest_streak_days,
  active_weeks, weeks_in_timeframe, active_weeks_share, by_weekday, by_month, by_year. The
  digest and dashboard switch from months to years past 24 months.
- `themes`: feature, fix, refactor, test, docs, ci_infra, performance, security, dependencies,
  other, each with prs, prs_merged, lines.
- `repo_share` (with `--repo-share`): per repo commits, commits_total, commit_share, lines,
  lines_total, line_share.
- `highlights.top_prs` (15, each with its author; score = log2(lines + 1) + reviews + comments
  + 2 × reviewers other than the author) and `highlights.top_repos` (10).
- `people`: one row per person, most active first: name, commits, prs_opened, prs_merged,
  reviews, issues_opened, lines_changed, active_days. The digest lists up to 25 for groups.

## Token budget
`budget.json` sums five parts: digest (at most 3,000), rubric plus writer instructions,
system overhead 5,000, output allowance 6,000, main conversation 3,000. Over `--max-tokens`
(default 25,000) the collector exits 2 and the skill asks before any writing starts.

## Limits
- GitHub counts commits on default branches only; squash-merged work counts through PR metrics.
- Contributor statistics (`--repo-share`) can answer HTTP 202 while GitHub computes them; the
  collector retries three times, then skips that repo with a warning.
- Old Enterprise Server versions may lack fields; partial answers become `warnings`.
- Team, organization and enterprise membership is read today; people who left during the
  timeframe are not included unless named with `user:`.

## Manual test
1. `export GITHUB_TOKEN=...` (scopes above) or `gh auth login`.
2. `PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --timeframe 30d --out /tmp/ir-test`
3. Expect exit 0, at most 15 lines, and the seven files listed above in `/tmp/ir-test`.
4. Open `dashboard.html` in a browser offline; charts render with no network.
5. Rerun step 2: it finishes without new API calls (`raw/` is reused); add `--refresh` to refetch.
6. Repeat step 2 with `--scope team:ORG/SLUG --timeframe "last quarter" --out /tmp/ir-team`:
   the scope line names the team and its people count, and `dashboard.md` has a People table.
7. In Claude Code: `claude --plugin-dir plugins/impact-review`, then `/impact-review:report 30d`
   and `/impact-review:report last quarter --scope team:ORG/SLUG`.

## Development
```
uv sync
uv run pytest
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/impact-review/src/impact_review
claude plugin validate .
```
Tests use recorded responses under `tests/fixtures/`; no test calls GitHub.
