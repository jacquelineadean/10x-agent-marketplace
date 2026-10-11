# 10x-agent-marketplace — Architecture

> High-level technical truth. Names used here are the names used everywhere else — do not
> invent parallel vocabulary. Update in the same change as the thing it describes.

## Overview
This repo is a Claude Code plugin marketplace with no server.
Claude Code reads `.claude-plugin/marketplace.json`, and users install plugins from `plugins/<name>/`.
Each plugin runs on the user's own machine inside Claude Code.

The first plugin, impact-review, splits work in two so model tokens stay low:
a Python **collector** does every API call and every calculation, and Claude reads only the small **digest** it writes.

```
 user ──/impact-review:report──▶ Claude Code (skill)
                                   │ 1. runs collector (Bash)
                                   ▼
                         collector (Python, stdlib only)
                           │ GraphQL + REST, read-only token
                           ▼
                     GitHub API (github.com / GHE Cloud / GHES / ghe.com)
                           │
                           ▼
       run folder (local, never committed)
         raw/  cached API responses   ← Claude never reads
         metrics.json, dashboard.md, dashboard.html
         digest.md  (a few KB)        ← Claude reads only this
                           │ 2. skill reads digest.md
                           ▼
         self-evaluation.md, resume-bullets.md, interview-stories.md
```

## Components and repositories
| Component | Responsibility | Tech | Owner |
| --- | --- | --- | --- |
| Marketplace manifest `.claude-plugin/marketplace.json` | Lists every plugin and where it lives | JSON | Jacqueline Dean |
| impact-review plugin shell `plugins/impact-review/` (`.claude-plugin/plugin.json`, `skills/`, `agents/`) | User-facing commands; tells Claude when to run the collector and how to write the synthesis | Markdown | Jacqueline Dean |
| impact-review collector `plugins/impact-review/src/impact_review/` | Calls GitHub, caches responses, computes metrics, renders dashboard and digest | Python 3.11+, standard library only at runtime | Jacqueline Dean |

The collector follows the standard `cli` layout (see CODEMAP.md):
`core/` holds metric rules with no I/O, `connectors/github/` holds every GitHub call,
`entrypoints/cli/` parses arguments, `config/` reads environment variables, and `__main__.py` wires them.

## Data flow
1. The user runs `/impact-review:report` with an optional timeframe (default year to date), host and org filter.
2. The skill runs the collector through Bash.
3. The collector resolves the token, identifies the user, then fetches contributions, pull requests, reviews, issues and commits for the timeframe.
4. Raw responses are cached in the run folder, so a rerun makes no repeat API calls.
5. `core/` computes metrics and writes `metrics.json`, `dashboard.md`, `dashboard.html` and `digest.md`.
6. The skill reads `digest.md` only, then writes the three synthesis files into the same run folder.

## Tech stack and tools
- Python 3.11+; runtime uses the standard library only (`urllib`, `json`), so installs need no package downloads.
- `uv` manages the dev environment: `ruff` (format and lint), `mypy` strict, `pytest`.
- GitHub GraphQL API v4 (contribution collection, search) and REST API v3 (repository contributor statistics).
- Claude Code plugin system: marketplace, plugins, skills, agents.

## Deployment and environments
- No hosted environment; plugins run on each user's machine.
- Distribution: `/plugin marketplace add jacquelineadean/10x-agent-marketplace`, then `/plugin install impact-review@10x-agent-marketplace`.
- Releases: each plugin carries a semantic version in `plugin.json`; a git tag `impact-review-vX.Y.Z` marks each release.
- Rollback: reinstall from the previous tag, or pin the marketplace to it.

## Boundaries and contracts
- Plugin to GitHub: the public GitHub APIs, versioned by GitHub; every call lives in `connectors/github/`.
- Skill to collector: command-line flags in, files out. The `metrics.json` and `digest.md` shapes carry a `schema_version` and are described in the plugin README.
- Single repo, so there is no `CONTRACTS/` folder.

## Cross-cutting concerns
- **Auth:** token from `GITHUB_TOKEN` or `GH_TOKEN`, else `gh auth token --hostname <host>`. Read-only use only. Enterprise orgs with single sign-on need an SSO-authorized token.
- **Privacy:** run folders hold corporate data. They live outside the repo by default, and `.gitignore` blocks them inside it. Nothing is sent anywhere except GitHub API requests.
- **Model tokens:** Claude never reads raw responses or `metrics.json` in full; the digest has a fixed size cap.
- **Rate limits:** GraphQL allows 5,000 points per hour; the collector caches, paginates in pages of 100 and backs off on secondary limits.
- **Secrets in logs:** the collector never prints the token or request headers.
- **Observability:** progress and warnings go to stderr; outputs go to files.

## Local development
```bash
uv sync                                   # install dev tools
uv run pytest                             # tests
uv run ruff format --check . && uv run ruff check .
uv run mypy                               # strict type check
python3 <groundwork>/engine/groundwork.py verify   # all of the above
claude --plugin-dir plugins/impact-review # try the plugin in Claude Code
```
