# Releasing

release-please versions and tags each plugin on its own.
Jacqueline Dean approves every release by merging its release PR (PROJECT.md).
The kit other repos copy is in `.github/release-kit/`.

## How a release happens

1. A PR with a `feat`, `fix`, `perf` or `revert` title touching `plugins/<name>/` is squash-merged to `main`.
2. `.github/workflows/release.yml` runs `release-please.yml`.
   release-please opens or updates one PR titled `chore(release): release main`.
3. That PR changes, for each plugin with releasable commits:
   - `plugins/<name>/.claude-plugin/plugin.json`: `version`
   - `.claude-plugin/marketplace.json`: the plugin's `version`
   - `.release-please-manifest.json`: the plugin's entry
   - `plugins/<name>/CHANGELOG.md`: a new section built from the PR titles
4. Merging the release PR tags `<name>-v<version>` (e.g. `chronicle-v0.5.0`) and creates a GitHub Release with the changelog section as notes.
5. `ci.yml` runs the full CI on the merged commit, as on every push to `main`.
6. Users get the release with `/plugin marketplace update 10x-agent-marketplace`, because the marketplace installs from `main`.

Commits outside `plugins/` (docs at the root, CI, `DECISIONS/`) never cut a release.
`.claude-plugin/marketplace.json` `metadata.version` changes only by hand, when the marketplace's own shape changes.

## Deployment checklist

Work through this on the release PR before merging it.

Before merge:

- [ ] CI is green on the release PR. With the `GITHUB_TOKEN` fallback, CI does not run on it; run `groundwork.py verify` on its branch locally.
- [ ] Each version bump matches the commits: a `feat` gives a minor bump, only `fix` or `perf` a patch.
- [ ] Each breaking change has a `BREAKING CHANGE:` note saying what users must do.
- [ ] Each changelog line reads as a user-facing change. To fix one, add a `BEGIN_COMMIT_OVERRIDE` ... `END_COMMIT_OVERRIDE` block with the corrected title to the merged PR's body; the next Release run rewrites the release PR.
- [ ] RFCs behind new features are approved, and specs in `specs/` match the shipped behaviour.
- [ ] Each released plugin's README states install steps, required token scopes and a manual test (CONSTITUTION.md).
- [ ] The manual test in each released plugin's README passes in a fresh session: `claude --plugin-dir plugins/<name>`.
- [ ] No run folder, raw API data, token or `.env` file is in the diff since the last tag: `git diff --stat <name>-v<old>..HEAD`.

After merge:

- [ ] The Release workflow created one tag and one GitHub Release per bumped plugin.
- [ ] CI passed on the merge commit.
- [ ] `/plugin marketplace update 10x-agent-marketplace` then `/plugin` shows the new versions.
- [ ] Teammates are told about any breaking change.

## Rollback

A release is a tag on `main`, so a rollback is a new release.

1. Revert the faulty PR: `git revert <sha>` on a `revert/<slug>` branch, titled `revert: <original title>`.
2. Merge it. release-please opens a patch release PR; merge that.
3. Users run `/plugin marketplace update 10x-agent-marketplace`.

Never delete or move a published tag; installs and changelog links point at it.

## Hotfix on an older line

Use this only when `main` holds unreleased work that must not ship with the fix.

1. `git switch -c release/<name>-<major>.<minor>.x <name>-v<version>` and push it.
2. Merge `fix:` PRs into that branch. A `feat:` there would bump the minor version.
3. release-please opens a patch release PR against that branch, because the reusable workflow passes the pushed branch as `target-branch`.
4. Merge it to tag `<name>-v<major>.<minor>.<patch+1>`.
5. Cherry-pick the fix to `main` in a PR with the same title.

Users on the marketplace follow `main`. A hotfix line reaches them only through a marketplace entry pinned to its tag.

## One-time setup

Repository settings, all by an admin:

- [ ] General, Pull Requests: allow squash merge only, with "Default to pull request title"; turn on "Automatically delete head branches".
- [ ] Rules: protect `main` and `release/**` with a required review from code owners, the `CI` and `PR lint` checks, linear history and no force pushes.
- [ ] Actions, General: allow GitHub Actions to create pull requests (needed for the `GITHUB_TOKEN` fallback).
- [ ] Release token: a GitHub App with Contents, Issues and Pull requests write, saved as the variable `RELEASE_APP_CLIENT_ID` and the secret `RELEASE_APP_PRIVATE_KEY`; or a fine-grained PAT as the secret `RELEASE_TOKEN`. With either, CI runs on release PRs.
- [ ] Baseline tags on the commit that shipped today's versions: `impact-review-v0.1.0`, `chronicle-v0.4.0`, `speedup-v0.1.0`. Without them, `bootstrap-sha` in `release-please-config.json` limits the first release to commits after that SHA.
- [ ] Code security: turn on Dependabot alerts, secret scanning and push protection.

## Files

| File | Role |
| --- | --- |
| `release-please-config.json` | One package per plugin, the files each release bumps, changelog sections, PR title |
| `.release-please-manifest.json` | The released version of each plugin |
| `.github/workflows/release.yml` | Runs release-please on pushes to `main` and `release/**` |
| `.github/workflows/release-please.yml` | The reusable release job, shared with other repos |
| `.github/workflows/ci.yml` | The quality gates and manifest checks |
| `.github/workflows/pr-lint.yml` | PR title and branch name rules |
| `.github/scripts/check-versions.sh` | Fails when plugin.json, marketplace.json and the manifest disagree |
| `plugins/<name>/CHANGELOG.md` | Release notes per plugin, written by release-please |
