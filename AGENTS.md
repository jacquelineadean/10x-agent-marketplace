# AGENTS.md — 10x-agent-marketplace

Instructions for coding agents in this standalone repo. Humans: read PROJECT.md first.

## Read before you write anything
1. `PROJECT.md` — what we build and why, and who to ask.
2. `ARCHITECTURE.md` — the components and their names.
3. `CONSTITUTION.md` — non-negotiable rules (scripts compute, Claude writes; local and read-only).
4. `DECISIONS/` — RFCs, approved or not.
5. The spec for the feature you touch: `specs/NNN-slug/`.
6. `CONTRIBUTING.md` and `RELEASING.md` — branch names, PR titles, checks and the release flow.

## Commands
**Python uses `uv`, never `pip`.** `uv add --dev <pkg>` for dev tools, `uv sync` to install, `uv run <cmd>` to run.
Commit `uv.lock`; never edit it by hand. Plugin runtime code uses the standard library only (CONSTITUTION.md); chronicle's painter adds NumPy and OpenCV, pending RFC-0002.

```bash
uv sync                                    # install dev tools (ruff, mypy, pytest)
uv run pytest                              # tests
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/impact-review/src/impact_review
uv run mypy packages/chronicle-engine/src/chronicle_engine
uv run mypy plugins/chronicle/src/chronicle
uv run mypy plugins/speedup/src/speedup
uv run mypy plugins/tokenwise/src/tokenwise
uv run mypy packages/sources/src/sources
uv run mypy plugins/briefing/src/briefing
uv run mypy plugins/blueprint/src/blueprint
claude plugin validate .                   # marketplace and plugin manifests
.github/scripts/check-versions.sh          # plugin.json, marketplace.json and release manifest agree
claude --plugin-dir plugins/impact-review  # try one plugin in a session
```
All four checks must pass before "done". CI (`.github/workflows/ci.yml`) runs the same checks on every PR.

## Where code lives
**Read `CODEMAP.md` before searching the code.** It lists every code folder and what it holds.
After adding, moving or removing a folder, update `CODEMAP.md` by hand and describe the folder in its Holds column.
Each plugin uses the same `cli` layout under `plugins/<name>/src/<package>/`:
`core/` (no I/O), `connectors/github/` (all GitHub calls), `entrypoints/cli/`, `config/` (only env reads), `__main__.py` (wiring).

## Conventions
- One plugin per folder: `plugins/<name>/` with `.claude-plugin/plugin.json`, `skills/`, optional `agents/`, `README.md`.
- Code shared by plugins lives once under `packages/<name>/`; a plugin links it into its own `src/` (Claude Code copies linked files at install). The engine imports no plugin.
- Register every plugin in `.claude-plugin/marketplace.json`, `release-please-config.json` and `.release-please-manifest.json`, and add its name to the scopes in `.github/workflows/pr-lint.yml`.
- Never edit a `version` field or a `CHANGELOG.md` by hand: release-please bumps `plugin.json` and `marketplace.json` together when its release PR merges (RELEASING.md). A new plugin starts at `0.0.0`, so its first release PR makes `0.1.0`.
- Branch names and PR titles follow CONTRIBUTING.md: `<type>/<slug>` branches, Conventional Commit titles such as `fix(speedup): ...`. PRs are squash-merged, so the title is the changelog line.
- No top-level `bin/` folder in a plugin: claude.ai and Cowork refuse to install those. Skills call scripts through `${CLAUDE_PLUGIN_ROOT}`.
- Skills tell Claude to read the digest only; never point a skill at raw API data or full `metrics.json`.
- Tests use recorded responses and transcript lines under `tests/fixtures/` (GitHub, Datadog, Prometheus, each sources collector and tokenwise sessions) and stand-in psql and SQLcl programs; no test calls a live API or database.
- Test files outside a package need unique names across plugins (speedup uses `test_speedup_*.py` and `speedup_helpers.py`; tokenwise `test_tokenwise_*.py` and `tokenwise_helpers.py`; the engine `test_engine_*.py`; sources `test_sources_*.py`; briefing `test_briefing_*.py` and `briefing_helpers.py`; blueprint `test_blueprint_*.py` and `blueprint_helpers.py`).
- Run folders and anything under `impact-review-runs/`, `chronicle-runs/`, `speedup-runs/` or `tokenwise-runs/` are git-ignored; never commit them.

## Code quality
Run the commands below after every change and fix what fails. Never weaken a rule,
add an ignore comment or skip a test to make it pass; an ignore needs a reason on the same line.

- format: `uv run ruff format --check .`
- lint: `uv run ruff check .`
- types: `uv run mypy plugins/impact-review/src/impact_review`, `uv run mypy packages/chronicle-engine/src/chronicle_engine`, `uv run mypy plugins/chronicle/src/chronicle`, `uv run mypy plugins/speedup/src/speedup`, `uv run mypy plugins/tokenwise/src/tokenwise`, `uv run mypy packages/sources/src/sources`, `uv run mypy plugins/briefing/src/briefing` and `uv run mypy plugins/blueprint/src/blueprint`
- test: `uv run pytest`

1. Reuse before writing: look in CODEMAP.md and search for an existing function first. Never copy-paste a block.
2. Make the smallest change that meets the spec. No speculative abstractions, options or layers.
3. Never swallow errors (no empty catch, no blind `except Exception`). Handle them at the entry point.
4. Validate input where it enters (routes, commands, consumers). Parameterised SQL only; no shell built from input.
5. Add a dependency only with the package manager, after checking it exists and is maintained; prefer what is already used.
6. Comments say why, never what. No commented-out code; no TODO without a tracked item.
7. Names come from the domain (PROJECT.md glossary); no Manager/Helper/Util names.
8. Test behaviour through public functions; mock only connectors to outside systems. A test must fail when the code is wrong.
9. Log through the project's logger, never print in core code, and never log secrets or personal data.
10. Keep files under the size limit and functions short; split by responsibility.

## Process
Change behaviour ⇒ update the plugin README in the same change. Jacqueline Dean reviews and merges every pull request.

## Repositories
- 10x-agent-marketplace — this repo — Claude Code marketplace holding every plugin.
