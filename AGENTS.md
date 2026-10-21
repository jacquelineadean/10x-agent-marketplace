# AGENTS.md — 10x-agent-marketplace

Instructions for coding agents in this standalone repo. Humans: read PROJECT.md first.

## Read before you write anything
1. `PROJECT.md` — what we build and why, and who to ask.
2. `ARCHITECTURE.md` — the components and their names.
3. `CONSTITUTION.md` — non-negotiable rules (scripts compute, Claude writes; local and read-only).
4. `DECISIONS/` — RFCs, approved or not.
5. The spec for the feature you touch: `specs/NNN-slug/`.

## Commands
**Python uses `uv`, never `pip`.** `uv add --dev <pkg>` for dev tools, `uv sync` to install, `uv run <cmd>` to run.
Commit `uv.lock`; never edit it by hand. Plugin runtime code uses the standard library only (CONSTITUTION.md); chronicle's painter adds NumPy and OpenCV, pending RFC-0002.

```bash
uv sync                                    # install dev tools (ruff, mypy, pytest)
uv run pytest                              # tests
uv run ruff format --check . && uv run ruff check .
uv run mypy plugins/impact-review/src/impact_review
uv run mypy plugins/chronicle/src/chronicle
uv run mypy plugins/speedup/src/speedup
claude plugin validate .                   # marketplace and plugin manifests
claude --plugin-dir plugins/impact-review  # try one plugin in a session
```
All four checks must pass before "done"; `groundwork.py verify` runs them together.

## Where code lives
**Read `CODEMAP.md` before searching the code.** It lists every code folder and what it holds.
After adding, moving or removing a folder, run `groundwork.py codemap` and describe the new folder in its Holds column.
Layout is the GroundWork standard `cli` profile, rooted at `plugins/impact-review/src/impact_review`:
`core/` (no I/O), `connectors/github/` (all GitHub calls), `entrypoints/cli/`, `config/` (only env reads), `__main__.py` (wiring).

## Conventions
- One plugin per folder: `plugins/<name>/` with `.claude-plugin/plugin.json`, `skills/`, optional `agents/`, `README.md`.
- Register every plugin in `.claude-plugin/marketplace.json` and bump its `version` in `plugin.json` on each release.
- No top-level `bin/` folder in a plugin: claude.ai and Cowork refuse to install those. Skills call scripts through `${CLAUDE_PLUGIN_ROOT}`.
- Skills tell Claude to read the digest only; never point a skill at raw API data or full `metrics.json`.
- Tests use recorded GitHub, Datadog and Prometheus responses under `tests/fixtures/`; no test calls a live API.
- Test files outside a package need unique names across plugins (speedup uses `test_speedup_*.py` and `speedup_helpers.py`).
- Run folders and anything under `impact-review-runs/`, `chronicle-runs/` or `speedup-runs/` are git-ignored; never commit them.

## Code quality
Run `groundwork.py verify` after every change (it runs the commands below) and fix what fails. Never weaken a rule,
add an ignore comment or skip a test to make it pass; an ignore needs a reason on the same line.

- format: `uv run ruff format --check .`
- lint: `uv run ruff check .`
- types: `uv run mypy plugins/impact-review/src/impact_review`, `uv run mypy plugins/chronicle/src/chronicle` and `uv run mypy plugins/speedup/src/speedup`
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

## Process (enforced by the groundwork plugin)
Interview → RFC → human approval → spec → plan → tasks → evals → implement → handover.
Change behaviour ⇒ change the spec in the same change. Only Jacqueline Dean approves, with `/groundwork-specflow:approve`.

## Repositories
- 10x-agent-marketplace — this repo — Claude Code marketplace holding every plugin.
