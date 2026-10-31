# Spec 001: impact-review, GitHub contribution metrics and review synthesis

Source: [RFC-0001](../../DECISIONS/RFC-0001-impact-review-github.md), extended by [RFC-0007](../../DECISIONS/RFC-0007-impact-review-any-scope-any-timeframe.md). Plugin: `plugins/impact-review/`.
Each acceptance criterion names the test that checks it (`plugins/impact-review/tests/`) or a manual check in the plugin README.

## Acceptance criteria

| ID | Criterion | Check |
| --- | --- | --- |
| AC-1 | Timeframes parse: `ytd` (default), `qtd`, `mtd`, `last week/month/quarter/year`, rolling `Nd/Nw/Nm/Nq/Ny`, `YYYY`, `YYYY-Qn`, `YYYY-MM`, `all time`, `A..B`, `A..`; future and unknown forms fail with a message | `test_timeframe.py` |
| AC-2 | Ranges over one year are split into chunks of at most one year, results deduplicated | `test_timeframe.py::test_year_chunks_*`, `test_source.py::test_ranges_over_a_year_*` |
| AC-3 | Endpoints derive from host: github.com, Enterprise Server, ghe.com | `test_settings_hosts_token.py::test_endpoints_per_host_kind` |
| AC-4 | Token from `GITHUB_TOKEN`, then `GH_TOKEN`, then `gh auth token`; missing token names the fix | `test_settings_hosts_token.py::test_token_*`, `test_missing_token_*` |
| AC-5 | `.env` is read with the standard library and never overrides a set variable | `test_settings_hosts_token.py::test_dotenv_*` |
| AC-6 | Collector gathers, per person through `user(login:)`, totals, calendar, PRs (paged by 100), reviews, issues and default-branch commits per contributed repo, tagged with author or reviewer | `test_source.py::test_collect_gathers_every_contribution_kind`, `test_commits_use_the_viewer_node_id_*`, `test_group.py::test_group_collect_*` |
| AC-7 | `--org` keeps only matching owners, case-insensitive, before commit fetches | `test_source.py::test_org_filter_*` |
| AC-8 | `--repo-share` reads REST contributor statistics, retries HTTP 202 three times, then warns and skips | `test_source.py::test_repo_share_retries_202_*` |
| AC-9 | Raw responses are cached in `raw/`; a rerun makes no repeat API calls; `--refresh` refetches | `test_source.py::test_cache_*`, `test_cli.py::test_second_run_uses_the_cache` |
| AC-10 | Only GraphQL queries and REST GETs are sent; a mutation is refused before any request; only https | `test_transport.py::test_mutations_are_refused_*`, `test_plain_http_is_refused` |
| AC-11 | 401 is an auth error; SSO refusal (header or SAML message) names the organization or URL | `test_transport.py::test_401_*`, `test_saml_*`, `test_sso_header_*`, `test_cli.py::test_sso_error_*` |
| AC-12 | Secondary rate limits wait `Retry-After`; 5xx backs off 2, 4, 8 s then gives up | `test_transport.py::test_secondary_rate_limit_*`, `test_server_errors_*` |
| AC-13 | Partial GraphQL answers (old Enterprise Server) become `warnings`, not failures | `test_transport.py::test_partial_data_*`, `test_source.py::test_partial_graphql_errors_*` |
| AC-14 | The token never appears in logs, output lines or the raw cache | `test_transport.py::test_network_failure_*`, `test_source.py::test_raw_cache_never_contains_the_token`, `test_cli.py::test_collect_writes_*` |
| AC-15 | Volume, code, flow, collaboration, consistency, themes, repo share, highlights and people match RFC-0001 4.4 and RFC-0007 4.4 on the recorded data; reviews by a PR's own author are excluded | `test_metrics.py`, `test_group.py::test_group_metrics_*` |
| AC-16 | `metrics.json` carries `schema_version` 2 and every digest number carries its key | `test_cli.py::test_collect_writes_*`, `test_outputs.py::test_digest_labels_every_number_*` |
| AC-17 | `digest.md` never exceeds 12,000 bytes: top PR rows drop first, then a truncation note | `test_outputs.py::test_digest_drops_*`, `test_digest_truncates_*` |
| AC-18 | `dashboard.html` is offline: inline CSS and SVG, no script, link, src or href; titles escaped | `test_outputs.py::test_dashboard_html_is_offline_and_escaped` |
| AC-19 | `budget.json` sums five parts with the digest part capped at 3,000; over `--max-tokens` the collector exits 2 and says what to do | `test_outputs.py::test_budget_*`, `test_cli.py::test_over_cap_*` |
| AC-20 | The collector prints at most 15 lines and never the digest | `test_cli.py::test_collect_writes_*` |
| AC-21 | Default run folder is `~/impact-review-runs/<host>/<scope slug>/<since>_<until>/`, `IMPACT_REVIEW_RUNS` and `--out` override | `test_cli.py::test_default_run_folder_*`, `test_group.py::test_cli_team_run_*`, `test_scope.py::test_labels_and_run_folder_slugs` |
| AC-22 | `python -m impact_review` wires settings, token, transport and CLI | `test_cli.py::test_main_wires_*` |
| AC-23 | Marketplace and plugin manifests validate | `claude plugin validate .` |
| AC-24 | The skill runs the collector, stops on exit 2 until the user chooses, and hands only the run folder path to `impact-writer` | manual check, README "Manual test" step 6 |
| AC-25 | `impact-writer` reads `digest.md` and `rubric.md` only, writes `review.md`, `highlights.md` and `stories.md` in the voice the digest's scope line sets, cites keys, uses placeholders for unknown outcomes, replies in at most 5 lines | manual check, README "Manual test" step 6 |
| AC-26 | Live run against a real host finishes and `dashboard.html` opens offline | manual check, README "Manual test" steps 1 to 6 |
| AC-27 | `--scope` parses `me`, `user:`, `team:`, `org:` and `enterprise:`; bad forms fail before any request | `test_scope.py::test_scope_forms`, `test_bad_scopes_raise`, `test_group.py::test_cli_bad_scope_*` |
| AC-28 | Team, org and enterprise scopes resolve members (paged), limit repos to their organizations unless `--org` is given, and name a missing target or token scope | `test_group.py::test_team_scope_*`, `test_org_scope_*`, `test_enterprise_scope_*`, `test_missing_scope_targets_*`, `test_cli_org_flag_*` |
| AC-29 | `--exclude` drops people; `--max-people` stops before any contribution query | `test_scope.py::test_finish_scope_*`, `test_group.py::test_cli_max_people_*` |
| AC-30 | `all time` starts at the oldest account creation date in scope | `test_timeframe.py::test_all_time_*`, `test_group.py::test_cli_all_time_*` |
| AC-31 | Group runs copy `rubric-group.md`, the digest lists people with `people.<login>` keys, and the dashboard has a People table; individual runs copy `rubric-individual.md` and show no People section | `test_group.py::test_cli_team_run_*`, `test_group_metrics_*`, `test_outputs.py::test_digest_labels_*` |

## Behaviour notes
- Rolling `Nd` is N days inclusive of today; `Nm`, `Nq`, `Ny` start the day after the same date N months, quarters or years back, clamped to the month end.
- `last year`, `last quarter`, `last month` and `last week` are previous whole calendar periods; `1y` and `past year` are rolling.
- Year chunks: `[start, start + 365 days - 1 s]`, next chunk starts one second later.
- Highlight score: `log2(lines + 1) + reviews + comments + 2 × distinct reviewers other than the author`.
- Themes: labels first, then a conventional title prefix (`feat:`, `[docs]`, `chore(deps):`), then title keywords; else `other`.
- A repository whose contributor statistics stay at 202 is retried on the next run; everything else comes from the cache.

## Out of scope
See RFC-0001 section 9 and RFC-0007 section 7.
