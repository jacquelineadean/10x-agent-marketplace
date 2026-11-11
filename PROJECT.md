# 10x-agent-marketplace — Project

> Business context, not technical detail. Written for a new teammate, a stakeholder, or an
> agent that needs to know *why* this exists. Technical shape lives in ARCHITECTURE.md.
> Never guess a fact here: ask the user.

## What this is
A Claude Code plugin marketplace that holds Jacqueline Dean's agent extensions: plugins, skills, agents and commands.
Teammates add it once with `/plugin marketplace add` and install the plugins they want.
The first plugin, **impact-review**, turns GitHub activity for one person, a team, an organization or an enterprise over any timeframe into metrics and written material: individual reviews, resumes and interview stories, or team and organization impact reports.
The second, **chronicle** (RFC-0002 and RFC-0003, drafts), turns a brief plus facts from connected tools or pasted notes into an illustrated, interactive story page designed for its subject: a project's status for a steering committee, a launch, an onboarding handbook or a guide to a podcast. Its animation skill (RFC-0005, draft) makes standalone animations in the same style, including technical architecture diagrams, for web pages, docs, chat and slides.

The third, **speedup** (RFC-0006, draft), runs continuous performance optimization from monitoring data such as Datadog: it measures user journeys at p75 against targets, guards each win with a benchmark ceiling that only moves down, quantifies every change, and publishes a dashboard plus an optional blog-style write-up.

The fourth, **tokenwise**, cuts Claude Code token use: it audits session transcripts with deterministic rules, applies low-risk reversible settings fixes, recommends model, workflow and instruction changes with evidence, warns on retry loops and writes handoff files for fresh sessions.

The fifth, **contributing**, is skills only: it writes pull request descriptions a reviewer can approve on the first pass (template, screenshots and recordings, GitHub formatting), and branch names and commit messages that follow each repo's own rules.

## Who it is for
- Jacqueline Dean, owner and maintainer.
- Teammates who install the marketplace in Claude Code.

The problem today: a year of GitHub work is spread across many repos, pull requests and Insights pages.
Assembling it for a review, for one person or a whole team, takes hours of clicking, and the result has few numbers.

## What success looks like
Success for impact-review, phase 1:
- One command produces a metrics dashboard, a rubric-based review, highlight bullets and STAR stories for a chosen scope (default: the token's owner) and timeframe (default: year to date).
- It works against GitHub.com, GitHub Enterprise Cloud, GitHub Enterprise Server and GHE.com data residency hosts.
- Model token use stays flat as activity grows: Claude reads a compact digest, never raw API responses.
- Every number in the written output traces back to a value in the collected GitHub data.

## Scope
**In scope:** the marketplace scaffold; the impact-review plugin with GitHub data collection, computed metrics, a local dashboard and written synthesis; the chronicle plugin with story pages published as private Artifacts after the user confirms (pending RFC-0002), and standalone animations exported as files (pending RFC-0005).
The speedup plugin reads Datadog and Prometheus performance data read-only (pending RFC-0006). The tokenwise plugin reads local Claude Code transcripts read-only and writes only the project's `.claude/settings.local.json`. The contributing plugin has no code; its pull-request skill pushes a branch and opens a draft PR only when the user asks for one.
**Explicitly out of scope:** other data sources for impact-review (Claude, Cursor, Datadog, ServiceNow, PagerDuty, Jira, Confluence) and cross-source correlation, planned for phase 2; any hosted dashboard or server; storing or sending collected corporate data anywhere outside the user's machine.

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
- **Timeframe:** the inclusive start and end dates of one impact-review run; default year to date, any period up to all time.
- **Collector:** code that reads one system with keys from the environment and writes local files: impact-review's GitHub collector, and the sources package's script-lane collectors (one per system).
- **Contribution:** a commit, pull request, review or issue GitHub attributes to a person in scope inside the timeframe.
- **Digest:** the compact Markdown summary the collector writes for Claude to read.
- **Scope:** whose work a run covers: one person, a list of people, a team, an organization or an enterprise.
- **Synthesis:** the written outputs Claude produces from the digest: `review.md`, `highlights.md`, `stories.md`.
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
- **Animation:** an `animation.json` and the one self-contained SVG built from it, with its HTML, PNG, GIF and video exports; its kind is `diagram` (engine), `scene` or `rig` (chronicle), or `tad`, `sequence` or `erd` (blueprint).
- **TAD:** a technical architecture diagram: components (nodes), groups such as a VPC or vendors, links (edges) and flows, written as data; code places and routes it.
- **Step:** one beat of an animation with one caption; it shows, draws, focuses, pulses or sets states on parts, and runs flows.
- **Flow:** a path through a TAD's nodes, along its edges, that a packet runs during a step.
- **Timeline:** an animation's one clock; every moving part is a CSS keyframe track that spans it, so one delay seeks the whole figure.
- **Journey:** speedup's unit of speed: one thing a user does, timed from their side of the screen, measured at a percentile per day.
- **Proxy benchmark:** a command that prints a stable number for a hot path, such as an instruction count, used in place of noisy wall-clock time.
- **Ceiling:** the highest value a proxy may reach before CI fails; `tighten` only lowers it. The rule as a whole is the **ratchet**.
- **Change log:** `perf/changes.jsonl`, one optimization per line with its flag, rollout stage and proxy numbers.
- **Transcript:** a Claude Code session log under `~/.claude/projects/`, one JSON line per message block.
- **Finding:** one tokenwise audit result with a tier, evidence, advice and tokens at stake.
- **Tier:** a finding's risk: low (applied by code, undoable), medium (the user decides), high (changes what every session loads).
- **Weighted tokens:** tokens priced in input-token equivalents with Anthropic's cache and output multiples.
- **Handoff:** a Markdown file of facts and next steps that lets a fresh session continue a task.
- **Conventional Commit:** a PR title of the form `<type>(<scope>): <subject>`, such as `feat(chronicle): add a timeline block`; release-please reads it to pick the version bump.
- **Release PR:** the pull request release-please keeps open on `main` with the next version bumps and changelog entries; merging it tags and publishes the release.
- **Data folder:** speedup's local, never-committed folder of history, benchmark runs and outputs for one project.
- **Engine:** `packages/chronicle-engine`, the facts, page and animation code the chronicle plugins share; each links it into its own `src/`.
- **Gatherer:** the sources plugin's subagent that reads company systems through the session's connectors or the script-lane collectors and writes `facts.json`, `queries.json` and `digest.md`.
- **Recipe:** one system's page in the sources plugin: how to reach it, what to read and what never to do.
- **Queries file:** `queries.json` in a run folder: the query behind each fact, with its system, lane, connection, window and as-of date.
- **Lane:** how a fact was read: `mcp` through a connector in the session, or `script` through a collector with keys.
- **Request:** a script-lane entry's description of what to read, in the shape its system's recipe gives, such as a JQL count per month or one SQL statement.
- **SQL guard:** the check every statement passes before a collector connects: one `SELECT` or `WITH`, no write keyword or side-effect function, named parameters only.
- **Refresh:** `briefing refresh`: the script-lane queries run again over windows moved to the last complete period, and the page rebuilds with no model call; facts read through connectors show as not refreshed.
- **Named connection:** an entry in `connections.json` holding a system's host and the names of the variables with its keys, never a key.
- **Architecture block:** blueprint's page figure around a built animation, with part details, pins for decisions and a step player.
- **Prototype:** blueprint's layout of clickable screens behind tabs, fed by facts.
- **Solutions file:** blueprint's `solutions.json`: approaches to one design question, the inputs and settings a reader moves, scenarios, and a formula per measure and approach.
- **Approach:** one candidate design in a solutions file; a **variant** is an approach with its own setting values, added on the page to compare configurations.
- **Input:** a number the world sets, such as traffic; a **setting** is a number, switch or choice the team sets, with the configuration key it lands in.
- **Scenario:** named input values, such as a sale peak; a reader can save the inputs as they stand as one more.
- **Measure:** what decides a design question, computed per approach by formula: a p95 wait, failures, data age, cost. Its **budget** is the limit a value must meet.
- **Feel:** how a page plays a measure: a wait runs in real time, failures mark some of 100 requests.
- **Decision:** the JSON a reader copies from a solutions page (the chosen variant, its settings, the inputs), and the `decision.md` code writes from it for the implementation.
- **Scout:** blueprint's Haiku subagent that reads a repository into `context.md` or `locate.md` with a file and line on every statement.
- **Layout:** how a story file becomes a document: a scrolling `page`, a `deck` of 16:9 slides or a `dashboard`.
- **Brand kit:** `brand.json`, an organization's colors and fonts applied under every page's theme; `--brand` picks it.
- **Slice:** one precomputed copy of a dashboard block for one filter option, such as a team or a region.
- **Researcher:** chronicle's subagent that reads provided material and writes `research/facts.json`, a locator on every fact, and `research/material.md`, a digest under 12 KB.
- **Rig:** a figure drawn in parts (`data-rig`, `data-part`) that each turn about a pivot by a rule for their role: legs, flippers, head, tail, ear, wing, claw.
- **Gait:** what a rig does where it stands: `still`, `walk`, `swim`, `crawl`, or `graze` and `root` (head down at rest).
- **Panorama:** chronicle's block for a wide painting to drag along, with animals placed by their foot point, zones, a tide slider and a journal.
- **Journal:** the species a reader has found across a page's panoramas, kept in the browser's storage under one key.
- **Rooms:** chronicle's block of paintings joined by doorways, each with numbered details.
- **Tour:** chronicle's block for a painted map whose stops open a plate, rooms or a panorama, walked by a route in the page's bar.
- **Hole:** a quiz played as golf in a story with `game`: each pick is a stroke, scored against par; a **scorecard** totals the round.
- **Plate note:** a pen mark (circle, underline, arrow, cross, tick, box) with words, drawn over a plate after it develops.
- **Widget library:** drills written once and copied into runs by `chronicle widgets`: bundled with the plugin, in a repository's `.chronicle/widgets/` or in the user's config folder.
