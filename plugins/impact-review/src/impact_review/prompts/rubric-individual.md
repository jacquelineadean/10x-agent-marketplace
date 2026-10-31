# Individual review rubric (default for one person)

Used when the scope is one person: a self-evaluation, a manager's review draft, a promotion
packet, a resume refresh or interview preparation. Replace it with your own framework through
`--rubric PATH`. The writer covers each area below in one short section, cites a
`metrics.json` key for every number, and marks outcomes GitHub cannot know as
`[ADD OUTCOME: ...]`.

## Delivery and impact
What shipped, for whom, and what changed because of it. Lead with merged pull requests
(volume.prs_merged), the top pull requests (highlights.top_prs) and their themes (themes).

## Technical quality
Size and shape of the work: pull request size bands (code.size_bands), lines next to pull
request counts (code.lines_changed with volume.prs_merged), fixes and refactors (themes.fix,
themes.refactor), tests and docs (themes.test, themes.docs).

## Collaboration and review
Reviews given and their outcomes (volume.reviews, volume.reviews_approved,
volume.reviews_changes_requested), review comments (volume.review_comments), authors reviewed
(collaboration.authors_reviewed), reviewers of own work (collaboration.reviewers_of_own_prs),
time to first review (flow.first_review_hours_median).

## Ownership and reliability
Repositories and organizations touched (volume.repos_touched, volume.orgs_touched), issues
opened (volume.issues_opened), consistency (consistency.active_days,
consistency.longest_streak_days, consistency.active_weeks_share), time to merge
(flow.merge_hours_median, flow.merge_hours_p75).

## Growth and leadership
Reach beyond own repositories (collaboration.cross_repo_reach, collaboration.repos_reviewed_in),
security and infrastructure work (themes.security, themes.ci_infra), and work that set a
direction for others. Business outcomes go in `[ADD OUTCOME: ...]` placeholders.
