---
description: A full status page built from pasted notes. Checks the run folder, the build, fact tokens, the derive table and that missing numbers stay missing.
tags: [full, story]
max_turns: 120
timeout_seconds: 2400
allowed_tools: [Skill, Read, Glob, Grep, Bash, Write, Edit, TodoWrite]
expected_outcome: chronicle-runs/fare-app/build/artifact.html exists; story.json shows numbers only as tokens; facts.json computes the shares in its derive table and holds no budget figure.
---

I need an illustrated status page for the Riverside Transit board meeting on 30 October 2026. The point to land: the new fare app is on track to finish rollout by December. Use only these notes, there is nothing else to pull from. No brand guide; pick a look that suits a city bus and tram operator. Put the run in chronicle-runs/fare-app.

Notes (as of 30 Sep 2026):
- Source A is the Jira board FARE. Source B is the app analytics export dated 2026-09-30.
- Scope is 60 tickets. Tickets done, cumulative at month end: July 18, August 31, September 42. (Jira)
- Monthly active riders on the new app: July 12,400, August 19,800, September 27,300. (analytics)
- Stations with the new card readers live: 9 of 14. (Jira)
- Failed card taps per week fell from 140 in the first week of July to 35 in the last week of September. (analytics)
- The budget figure is not confirmed by finance yet, so leave it out.

Tell me how far through the scope we are, how many stations are live, and how much rider numbers grew since July.
