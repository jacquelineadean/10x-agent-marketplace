# impact-review

Turns one person's GitHub activity over a timeframe into metrics, an offline dashboard, a
self-evaluation draft, resume bullets and interview stories. A standard-library Python
collector makes every API call and every calculation; Claude reads only a 12 KB digest.

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

Required scopes: `repo`, `read:org`, `read:user`. Enterprise organizations with single sign-on
need the token authorized for SSO; the collector names the organization and the step when
GitHub refuses.

## Use
```
/impact-review:report                          # year to date on github.com
/impact-review:report last 365d --org acme     # one org, last 365 days
/impact-review:report 2026-01-01..2026-09-30 --host ghe.corp.example --repo-share
```
The skill runs the collector, shows at most 15 lines, then a Sonnet subagent (`impact-writer`)
reads `digest.md` and `rubric.md` and writes the three synthesis files.

Without Claude (zero model tokens):
```
PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --timeframe ytd
```
Flags: `--timeframe`, `--since/--until`, `--org` (repeatable), `--host`, `--out`, `--refresh`,
`--repo-share`, `--max-tokens` (default 25000), `--rubric`.
Exit codes: 0 done, 1 error (message on stderr), 2 token estimate over the cap.

Hosts: `github.com` (also Enterprise Cloud), `HOST` for Enterprise Server
(`https://HOST/api/graphql`, `https://HOST/api/v3`), `SUB.ghe.com` for data residency
(`https://api.SUB.ghe.com`).

## Run folder
Default `~/impact-review-runs/<host>/<login>/<since>_<until>/` (`IMPACT_REVIEW_RUNS` or `--out`
change it). Never commit it.

| File | Written by | Claude reads it? |
| --- | --- | --- |
| `raw/*.json` | collector (cache; a rerun makes no repeat API calls) | never |
| `metrics.json` | collector, `schema_version` 1 | never in full |
| `dashboard.md`, `dashboard.html` | collector; HTML is offline with inline SVG, no scripts | no |
| `digest.md` | collector, at most 12,000 bytes | yes, the only input |
| `budget.json` | collector, token estimate against the cap | no |
| `rubric.md` | copied from `--rubric` or the default five-area rubric | yes |
| `self-evaluation.md`, `resume-bullets.md`, `interview-stories.md` | impact-writer | written |

### metrics.json shape (schema_version 1)
Top-level keys: `schema_version`, `generated_at`, `host`, `profile`, `timeframe`, `volume`,
`code`, `flow`, `collaboration`, `consistency`, `themes`, `repo_share`, `highlights`, `limits`,
`warnings`. Every number in the digest carries its key, for example `(volume.prs_merged)`, and
the writer cites that key next to the number.

- `volume`: commits, prs_opened, prs_merged, prs_closed_unmerged, prs_open, reviews and
  outcomes, review_comments, issues_opened, repos_touched, orgs_touched, languages,
  restricted_contributions.
- `code`: lines_added, lines_deleted, lines_changed, files_changed, median_pr_lines, size_bands
  (under_10, 10_to_99, 100_to_499, 500_to_999, 1000_plus), commit_lines_added, commit_lines_deleted.
- `flow`: merge_hours_median, merge_hours_p75, first_review_hours_median, prs_with_review,
  prs_merged_per_week, weeks.
- `collaboration`: authors_reviewed, reviewers_of_own_prs, reviews_per_pr_opened,
  repos_reviewed_in, repos_reviewed_only, cross_repo_reach.
- `consistency`: contributions, active_days, days_in_timeframe, longest_streak_days,
  active_weeks, weeks_in_timeframe, active_weeks_share, by_weekday, by_month.
- `themes`: feature, fix, refactor, test, docs, ci_infra, performance, security, dependencies,
  other, each with prs, prs_merged, lines.
- `repo_share` (with `--repo-share`): per repo commits, commits_total, commit_share, lines,
  lines_total, line_share.
- `highlights.top_prs` (15, score = log2(lines + 1) + reviews + comments + 2 × reviewers) and
  `highlights.top_repos` (10).

## Token budget
`budget.json` sums five parts: digest (at most 3,000), rubric plus writer instructions,
system overhead 5,000, output allowance 6,000, main conversation 3,000. Over `--max-tokens`
(default 25,000) the collector exits 2 and the skill asks before any writing starts.

## Limits
- GitHub counts commits on default branches only; squash-merged work counts through PR metrics.
- Contributor statistics (`--repo-share`) can answer HTTP 202 while GitHub computes them; the
  collector retries three times, then skips that repo with a warning.
- Old Enterprise Server versions may lack fields; partial answers become `warnings`.

## Manual test
1. `export GITHUB_TOKEN=...` (scopes above) or `gh auth login`.
2. `PYTHONPATH=plugins/impact-review/src python3 -m impact_review collect --timeframe "last 30d" --out /tmp/ir-test`
3. Expect exit 0, at most 15 lines, and the seven files listed above in `/tmp/ir-test`.
4. Open `dashboard.html` in a browser offline; charts render with no network.
5. Rerun step 2: it finishes without new API calls (`raw/` is reused); add `--refresh` to refetch.
6. In Claude Code: `claude --plugin-dir plugins/impact-review`, then `/impact-review:report last 30d`.

## Development
```
uv sync
uv run pytest
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/impact-review/src/impact_review
claude plugin validate .
```
Tests use recorded responses under `tests/fixtures/`; no test calls GitHub.
