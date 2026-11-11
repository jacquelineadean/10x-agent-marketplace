# Contributing to 10x-agent-marketplace

This file covers branches, commits, pull requests and checks.
`AGENTS.md` holds the coding rules, `CONSTITUTION.md` the rules no change may break, and `RELEASING.md` the release steps.

## Flow

1. Open an issue with the bug or feature template, or start from an approved RFC in `DECISIONS/`.
2. Branch from `main` with a name from the table below.
3. Change the code, and the spec in `specs/` when behaviour changes (AGENTS.md, Process).
4. Run the checks in AGENTS.md (ruff, mypy, pytest) and `claude plugin validate .`; all must pass.
5. Open a pull request with a Conventional Commit title. The template lists the checks.
6. Jacqueline Dean reviews (CODEOWNERS). CI and PR lint must be green.
7. Squash-merge. The PR title becomes the one commit on `main` and the CHANGELOG line.

## Branch names

| Pattern | Use | Example |
| --- | --- | --- |
| `<type>/<slug>` | Every change; `<type>` is a commit type below | `feat/chronicle-timeline-block` |
| `<type>/<issue>-<slug>` | A change that closes an issue | `fix/42-ghes-sso-retry` |
| `release/<plugin>-<major>.<minor>.x` | A hotfix line cut from a release tag | `release/impact-review-0.2.x` |
| `release-please--*` | Opened by release-please; never by hand | `release-please--branches--main` |
| `dependabot/*` | Opened by Dependabot; PR lint skips it | `dependabot/uv/dev-tools-1a2b3c` |
| `claude/<slug>` | Opened by a Claude Code session | `claude/release-management-workflows-7mc214` |

Slugs are lower case with `a-z`, `0-9`, `.`, `_` and `-`.
`.github/workflows/pr-lint.yml` holds the exact patterns and fails a PR from any other branch.

## Commit and PR titles

Format: `<type>(<scope>)!: <subject>`. The scope and `!` are optional.

| Type | Use | Release |
| --- | --- | --- |
| `feat` | New skill, command, option or plugin | minor |
| `fix` | Wrong behaviour fixed | patch |
| `perf` | Faster with the same behaviour | patch |
| `revert` | Reverts an earlier commit | patch |
| `docs`, `refactor`, `test`, `build`, `ci`, `chore` | No user-visible change | none |

- Scopes: `impact-review`, `chronicle`, `speedup`, `tokenwise`, `sources`, `briefing`, `blueprint`, `contributing`, `marketplace`, `deps`, `release`, `security`.
  A new plugin adds its name to `pr-lint.yml` in the PR that adds the plugin.
- The subject starts lower case, uses the imperative ("add", "fix") and has no trailing period.
- `!` marks a breaking change. Below 1.0.0 it bumps the minor version, from 1.0.0 the major.
  The PR body then ends with a `BREAKING CHANGE: <what users must do>` footer.
  Renaming or removing a skill, a CLI flag or an output file is breaking.
- release-please files each commit under the plugin whose folder it touches.
  A PR that touches two plugins appears in both changelogs, so keep one plugin per PR where you can.

Examples:

```text
feat(impact-review): add --org filter for enterprise scope
fix(speedup): stop guard from reading a stale bench.json
feat(chronicle)!: rename the story skill's --out flag to --run
docs: describe the release flow in RELEASING.md
```

## Pull requests

- Keep a PR to one change. Over about 400 changed lines, split it.
- Fill in every section of `.github/pull_request_template.md`.
- Never edit a `version` field or a `CHANGELOG.md` by hand; release-please writes them.
- Mark a PR as draft until the checks pass.

## Checks on every PR

| Workflow | Job | What it checks |
| --- | --- | --- |
| `CI` | format, lint, types, tests | `uv sync --locked`, `ruff format --check`, `ruff check`, mypy on the 7 plugin packages and 2 shared packages, `pytest` |
| `CI` | plugin and release manifests | `.github/scripts/check-versions.sh` and `claude plugin validate .` |
| `PR lint` | Conventional Commit title | Type, scope and subject rules above |
| `PR lint` | Branch name | The branch patterns above |

Dependabot opens one grouped PR a week for GitHub Actions (`ci(deps): ...`) and one for dev tools in `uv.lock` (`chore(deps): ...`).
Neither type cuts a plugin release. PR lint skips Dependabot PRs; GitHub counts the skipped checks as passed.
