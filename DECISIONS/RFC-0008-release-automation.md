---
id: RFC-0008
title: CI and release automation with release-please
status: draft
classification: internal
signoffs_required: 1
requested_by: Jacqueline Dean
support: []
owner: Jacqueline Dean
supersedes: []
related_rfcs: []
author: Claude Code, for Jacqueline Dean
created: 2026-11-01
---

# RFC-0008 — CI and release automation with release-please

## 1. Summary
The repo has no CI, and each plugin version is bumped by hand in two files.
This RFC adds:

1. **CI** (`.github/workflows/ci.yml`): the four quality gates from AGENTS.md, `claude plugin validate .`, and a check that `plugin.json`, `marketplace.json` and the release manifest agree.
2. **PR lint** (`pr-lint.yml`): Conventional Commit titles with one scope per plugin, and branch name patterns.
3. **Releases** (`release.yml` calling `release-please.yml`): one release PR on `main`; merging it bumps each changed plugin, writes `plugins/<name>/CHANGELOG.md`, and tags `<name>-v<version>`.
4. **Repo hygiene**: a PR template, issue forms, CODEOWNERS, grouped weekly Dependabot PRs.
5. **A release kit** (`.github/release-kit/`) other repos copy to call the same reusable workflow.
6. **Docs**: `CONTRIBUTING.md` (branches, commits, PRs) and `RELEASING.md` (release flow, deployment checklist, rollback, hotfix, settings).

No plugin code or runtime behaviour changes.

## 2. The need
- PROJECT.md says Jacqueline Dean approves every release; today a release is an unreviewed hand edit of `version`.
- `marketplace.json` and `plugin.json` both carry each version, with nothing keeping them equal.
- The quality gates in CONSTITUTION.md run only when someone runs them locally.
- Users have no changelog to read before `/plugin marketplace update`.

**Done means:** a merged `feat(chronicle): ...` PR yields a release PR bumping chronicle to 0.5.0 in both manifests, with a changelog entry; merging it tags `chronicle-v0.5.0`.

## 3. Proposal

### 3.1 Versioning
- One release-please package per plugin folder, `release-type: simple`, component = plugin name.
- `extra-files` bump `$.version` in `plugin.json` and the plugin's entry in the root `marketplace.json` (a path with a leading `/` is relative to the repo root).
- `bump-minor-pre-major: true`: every plugin is 0.x, so a breaking change bumps the minor version until a plugin reaches 1.0.0.
- One grouped release PR, `chore(release): release main`, so two plugin bumps never conflict in `marketplace.json`.
- `bootstrap-sha` is the `main` commit before this change, so the first release reads only later commits.

### 3.2 Changes to the supplied kit
| Supplied | Changed to | Reason |
| --- | --- | --- |
| No `target-branch` | `target-branch: github.ref_name` | release-please targets the default branch otherwise, so hotfix release PRs on `release/**` went to `main` |
| `contents` and `pull-requests` write | adds `issues: write` | release-please creates its `autorelease` labels through the issues API |
| Root outputs only | adds `releases_created`, `paths_released`, `all` | multi-package repos had no way to tell which package released |
| Tags `@v4`, `@v5` | full commit SHAs | a tag can be moved to other code |
| PAT only | GitHub App token first, PAT second | an App token expires in an hour and belongs to no person |
| No concurrency | one run per ref, never cancelled | two quick pushes could race on the release PR |
| Default changelog | hidden `docs`, `chore`, `ci`, `test`, `refactor`, `build`; a Performance section | changelogs list user-facing changes only |
| Title type check | adds scopes, subject case and branch names | consistent changelog lines and branch names |

## 4. Alternatives considered
- **Changesets or semantic-release.** Rejected: both need Node tooling in a Python repo; release-please reads only commit titles and runs as one action.
- **One version for the whole marketplace.** Rejected by principle 5: each plugin has its own version.
- **Separate release PRs per plugin.** Rejected: each would edit `marketplace.json`, and merging one conflicts the others.
- **A Python script for the version check.** Rejected: 40 lines of shell with `jq` need no package, test path or CODEMAP entry.

## 5. Risks and objections
| Risk | Mitigation |
| --- | --- |
| Release PRs opened with `GITHUB_TOKEN` start no CI, so required checks never report | `RELEASING.md` setup: a GitHub App or PAT; the checklist says to run the AGENTS.md checks locally otherwise |
| A PR touching two plugins appears in both changelogs | CONTRIBUTING.md asks for one plugin per PR |
| release-please rewrites `marketplace.json` and `plugin.json` with `JSON.stringify` | both were reformatted to that layout in this change, so release diffs hold only the version |
| `claude plugin validate` runs a pinned npm package in CI | version pinned; the job has read-only permissions and no secrets |

## 6. Impact
- Constitution: CI writes tags and releases to this repo only. Principles 3 and 4 cover plugin runtime, so no amendment is needed.
- AGENTS.md: "bump its version on each release" becomes "release-please bumps it; never by hand".
- Plugin code, specs and tests: unchanged.

## 7. Open questions
1. GitHub App or fine-grained PAT for the release token?
2. Create the baseline tags `impact-review-v0.1.0`, `chronicle-v0.4.0`, `speedup-v0.1.0` and `tokenwise-v0.1.0` on the current `main`?
3. Should a plugin reaching 1.0.0 drop `bump-minor-pre-major` for that package only?
