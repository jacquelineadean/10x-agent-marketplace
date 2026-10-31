# Group review rubric (default for a team, an organization, an enterprise or a list of people)

Used when the scope holds more than one person: a team retrospective, a quarterly business
review, an engineering all-hands, an organization or enterprise report. Replace it with your
own framework through `--rubric PATH`. The writer covers each area below in one short
section, cites a `metrics.json` key for every number, names people only from the digest's
People section, and marks outcomes GitHub cannot know as `[ADD OUTCOME: ...]`.

## Delivery and impact
What the group shipped and where: merged pull requests (volume.prs_merged), the top pull
requests (highlights.top_prs), themes (themes) and the busiest repositories
(highlights.top_repos).

## Throughput and flow
How fast work moves: merged pull requests per week and per person (flow.prs_merged_per_week,
flow.prs_merged_per_person_per_week), time to first review (flow.first_review_hours_median),
time to merge (flow.merge_hours_median, flow.merge_hours_p75), pull request size bands
(code.size_bands).

## Quality and maintenance
Fixes, refactors, tests, docs, dependencies and security work (themes.fix, themes.refactor,
themes.test, themes.docs, themes.dependencies, themes.security), next to the pull request
counts they belong to.

## Collaboration
Review load and where it goes: reviews given (volume.reviews), reviews of the group's own work
against reviews of others (collaboration.reviews_inside_scope,
collaboration.reviews_outside_scope), reviewers from outside the group
(collaboration.reviewers_outside_scope), cross-repository reach
(collaboration.cross_repo_reach).

## Participation and consistency
How many people contributed (volume.active_people of volume.people), active days and weeks
(consistency.active_days, consistency.active_weeks_share), and how work spreads across people
(people). Describe spread and gaps; never rank or grade individuals.
