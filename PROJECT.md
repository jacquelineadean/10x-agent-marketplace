# 10x-agent-marketplace — Project

> Business context, not technical detail. Written for a new teammate, a stakeholder, or an
> agent that needs to know *why* this exists. Technical shape lives in ARCHITECTURE.md.
> Never guess a fact here: ask the user.

## What this is
A Claude Code plugin marketplace that holds Jacqueline Dean's agent extensions: plugins, skills, agents and commands.
Teammates add it once with `/plugin marketplace add` and install the plugins they want.
The first plugin, **impact-review**, turns one person's GitHub activity over a date range into metrics and written material for performance reviews, resumes and job interviews.
The second, **chronicle** (RFC-0002 and RFC-0003, drafts), turns a brief plus facts from connected tools or pasted notes into an illustrated, interactive story page designed for its subject: a project's status for a steering committee, a launch, an onboarding handbook or a guide to a podcast.

## Who it is for
- Jacqueline Dean, who uses the plugins daily and runs impact-review against a corporate GitHub Enterprise account.
- Teammates who install the marketplace in Claude Code.

The problem today: a year of GitHub work is spread across many repos, pull requests and Insights pages.
Assembling it for a self-evaluation takes hours of clicking, and the result has few numbers.

## Why now / what success looks like
End-of-year review season is the trigger.
Success for impact-review, phase 1:
- One command produces a metrics dashboard, a self-evaluation draft, resume bullets and interview stories for a chosen timeframe (default: year to date).
- It works against GitHub.com, GitHub Enterprise Cloud, GitHub Enterprise Server and GHE.com data residency hosts.
- Model token use stays flat as activity grows: Claude reads a compact digest, never raw API responses.
- Every number in the written output traces back to a value in the collected GitHub data.

## Scope
**In scope:** the marketplace scaffold; the impact-review plugin with GitHub data collection, computed metrics, a local dashboard and written synthesis; the chronicle plugin with story pages published as private Artifacts after the user confirms (pending RFC-0002).
**Explicitly out of scope:** other data sources (Claude, Cursor, Datadog, ServiceNow, PagerDuty, Jira, Confluence) and cross-source correlation, planned for phase 2; any hosted dashboard or server; storing or sending collected corporate data anywhere outside the user's machine.

## Who works on what
| Person | Role | Owns / ask them about | Contact (email / chat handle) |
| --- | --- | --- | --- |
| Jacqueline Dean | Owner and maintainer | Every plugin, all approvals and releases | GitHub @jacquelineadean |

## Stakeholders and decision makers
Jacqueline Dean signs off on scope, RFCs, specs and releases alone.
Teammates who install the marketplace are users with no sign-off role.

## Repositories in this product
- `10x-agent-marketplace` — this repo; the Claude Code marketplace and every plugin in it; owner Jacqueline Dean.

## Glossary
- **Marketplace:** a git repo with `.claude-plugin/marketplace.json` that lists plugins Claude Code can install.
- **Plugin:** a folder with `.claude-plugin/plugin.json` plus skills, agents, commands or hooks.
- **Skill:** a `SKILL.md` file of instructions Claude loads on demand, invoked as `/<plugin>:<skill>`.
- **Timeframe:** the inclusive start and end dates of one impact-review run; default year to date.
- **Collector:** the impact-review Python command that calls GitHub APIs and writes local files.
- **Contribution:** a commit, pull request, review or issue GitHub attributes to the user inside the timeframe.
- **Digest:** the compact Markdown summary the collector writes for Claude to read.
- **Synthesis:** the written outputs Claude produces from the digest: self-evaluation draft, resume bullets, interview stories.
- **Run folder:** the local, never-committed folder holding one run's data and outputs.
- **Story:** chronicle's `story.json`: the chapters and blocks of one page, with numbers only as fact tokens.
- **Facts file:** chronicle's `facts.json`: every number and date on a page, each with its source and a note.
- **Derive table:** the part of a facts file that names numbers computed by code from other facts.
- **Plate:** a watercolor painting on a story page; it can carry moving layers and hotspots.
- **Theme:** a story's identity taken from its subject: palette, fonts, progress device, chapter marks and stat style.
- **Drawing:** an SVG file Claude writes for a plate; chronicle paints it in ink and watercolor.
- **Widget:** a script Claude writes for one page when no block fits; `chronicle check` lints it.
- **Preset:** a named, composed painting such as `bridge-hero`; **motif:** a paintable element such as `sky` or `arch_bridge`.
- **Artifact:** a web page hosted privately on claude.ai, where a story page is published.
