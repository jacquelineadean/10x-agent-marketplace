---
id: RFC-0007
title: impact-review 0.2: any scope, any timeframe
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
request_source: Claude project thread "Personal info cleanup", 31 Oct 2026
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: [RFC-0001]
author: Claude Code, for Jacqueline Dean
created: 2026-10-31
---

# RFC-0007 — impact-review 0.2: any scope, any timeframe

## 1. Summary
impact-review 0.1 reviewed one GitHub account, the token's owner, over `ytd`, `last Nd` or a
date range. Version 0.2 reviews any **scope**: the token's owner, a list of people, one or
more teams, one or more organizations, or an enterprise. It takes any **timeframe**: to date
(`ytd`, `qtd`, `mtd`), previous whole periods (`last month`, `last quarter`, `last year`),
rolling windows (`30d`, `3m`, `1y`), calendar periods (`2025`, `2026-Q3`, `2026-03`), `all
time`, and ranges. Metrics work in aggregate and per person; the writer adapts its voice and
rubric to an individual or a group. The default run (`--scope me --timeframe ytd`) produces
the same numbers as 0.1.

## 2. The need
**User scenario:** the request asked for the plugin to be generic, reusable for individual,
team, organization and enterprise reviews, over any timeframe with year to date as the
default (examples given: 1 month, 1 year, all time).
**Done means:** one command reviews any of the five scope kinds over any of the timeframe
forms in section 4.2; group runs show people counts, a per-person table and review traffic
inside and outside the group; every number still traces to `metrics.json`.

## 3. Decisions
| # | Question | Decision | Why |
| --- | --- | --- | --- |
| 1 | How is a person's activity read? | `user(login:)` contributionsCollection, the same fields 0.1 read from `viewer` | One query path for every person; the token owner is one more login |
| 2 | Where do team, org and enterprise members come from? | `team.members(membership: ALL)`, `organization.membersWithRole`, `enterprise.organizations` then each organization's members | Needs `read:org`, plus `read:enterprise` for enterprises; enterprise admin rights are not required |
| 3 | Which repositories count for a group? | Team, org and enterprise scopes keep repositories their organizations own; `--org` overrides | A team review should not count members' open-source side work |
| 4 | How large can a run get? | `--max-people` (default 100) stops before any contribution query; `--exclude` drops logins | Each person costs about five queries per year of timeframe plus one per repository |
| 5 | Where does `all time` start? | The oldest `createdAt` among the people in scope; 2008-01-01 when unknown | GitHub has no contributions before an account exists |
| 6 | Does `last year` mean the previous calendar year or the past 365 days? | Previous calendar year; `1y` and `past year` are rolling | Matches `last month` and `last quarter`, and the README table states both |
| 7 | What do the written outputs become? | `review.md`, `highlights.md`, `stories.md` for every scope | The 0.1 names (`self-evaluation.md`, `resume-bullets.md`, `interview-stories.md`) only fit one person |
| 8 | Which rubric is the default? | `rubric-individual.md` for one person, `rubric-group.md` otherwise | Group reviews need throughput and participation sections, and must not grade individuals |
| 9 | Version | Plugin 0.2.0; `metrics.json` schema_version 2 (`profile` becomes `scope`, `people` added) | Code and output shape change |

## 4. Design
### 4.1 Scope (`core/scope.py`)
`parse_scope` turns `me`, `user:a,b`, `team:ORG/SLUG[,ORG/SLUG]`, `org:ORG[,ORG]` or
`enterprise:SLUG` into a request. The GitHub connector resolves it to people and the
organizations it limits work to. `finish_scope` drops excluded and duplicate logins and
enforces the people cap. A `Scope` carries `label`, `is_individual`, `logins` and the run
folder `slug` (`<login>`, `team-ORG-SLUG`, `org-ORG`, `enterprise-SLUG`, `users-a+b`, hashed
past 60 characters).

### 4.2 Timeframe (`core/timeframe.py`)
| Form | Range |
| --- | --- |
| `ytd` (default), `qtd`, `mtd`, `this year/quarter/month` | period start to today |
| `last week/month/quarter/year` | previous whole calendar period |
| `Nd`, `Nw`, `Nm`/`Nmo`, `Nq`, `Ny`, with optional `last`/`past` and spelled units | rolling, ending today; months clamp to the month end |
| `YYYY`, `YYYY-Qn`, `YYYY-MM` | that period, ending today at the latest |
| `all time` | oldest account in scope to today |
| `A..B`, `A..` | inclusive range; open end is today |

A period that starts after today is an error. Ranges over a year still split into year chunks.

### 4.3 Collection
Per person: year chunks of contributions, pull requests, reviews and issues, then
default-branch commits for that person's repositories by node id. Items carry their author
(reviews their reviewer). The merged activity dedupes pull requests and issues by URL,
reviews by URL, time and reviewer, and commits by repository and oid (two people can share a
commit). Daily calendars sum across people and stay available per person.
`--repo-share` counts every login in scope toward the share.

### 4.4 Metrics added or changed
- `scope`: kind, targets, label, individual, people, orgs.
- `volume.people`, `volume.active_people`.
- `flow.prs_merged_per_person_per_week`; first review excludes reviews by the PR's author.
- `collaboration`: `authors_reviewed_outside_scope`, `reviewers_outside_scope`,
  `reviews_inside_scope`, `reviews_outside_scope`; self-review means reviewer equals author.
- `consistency.by_year`; the digest and dashboard switch from months to years past 24 months.
- `highlights.top_prs[].author`; the score's reviewer term excludes the author.
- `people`: one row per person (commits, PRs opened and merged, reviews, issues, merged
  lines, active days), most active first. The digest lists up to 25 for groups and drops
  rows in fives before truncating.

### 4.5 Writer
`impact-writer` reads the digest's `Scope:` line. Individual scope: first person, a review
draft, resume bullets, interview stories. Group scope: third person, an impact report,
update bullets, case studies; people are named only from the People section and never
ranked or graded. Caps, citation rules and the six-turn budget are unchanged.

## 5. Alternatives considered
- **Search API (`author:LOGIN`) in place of contributionsCollection.** Rejected: 1,000-result
  cap per query and no review or calendar data.
- **Enterprise members through `enterprise.members`.** Rejected: needs enterprise owner
  rights; the organization route works for any member with `read:enterprise`.
- **Separate plugins for individual and team reviews.** Rejected: the collector, metrics
  and outputs are the same code with a different people list.
- **Keep the 0.1 output file names for individuals.** Rejected: two naming schemes for one
  writer; the README maps each file to its individual and group use.

## 6. Risks
- Large organizations: 300 people over a year is about 1,500 GraphQL queries before commits.
  The people cap, the `raw/` cache and the secondary rate-limit handling from RFC-0001 bound it.
- Membership is read on the run date. People who left during the timeframe are missing
  unless named with `user:`. Stated in the README Limits.
- Private work of other people shows only in repositories the token can read. Stated in
  `metrics.json` limits and the digest.
- A group digest can name individuals. The group rubric and writer rules forbid ranking or
  grading people.

## 7. Out of scope
Non-GitHub sources (RFC-0001 phase 2), historical team membership, per-person dashboards in
one run (run `user:LOGIN` for each), and comparisons between two timeframes.
