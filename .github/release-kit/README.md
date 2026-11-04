# Release kit: automated releases with release-please

This folder holds the files another repository copies to get the same release flow as this
marketplace. The reusable workflow itself lives at `.github/workflows/release-please.yml` here,
so every repo runs one reviewed copy of it.

## How it works

1. Developers squash-merge pull requests whose title is a Conventional Commit.
   `pr-lint.yml` rejects a title or branch name that breaks the rules.
2. On each push to `main` or `release/**`, release-please reads the commits since the last tag.
   It computes the next semantic version per package.
3. It opens or updates one release PR with the version bumps and the `CHANGELOG.md` entries.
   The PR title is `chore(release): ...`, which passes the title check.
4. Merging the release PR creates the tag and the GitHub Release, with the changelog entry as release notes.
5. The caller's `publish` job then checks out that tag, builds it and ships it.

## Bump rules

| Commit title | Bump from 1.4.2 | Bump below 1.0.0 (`bump-minor-pre-major`) |
| --- | --- | --- |
| `fix:`, `fix(deps):`, `fix(security):`, `perf:`, `revert:` | 1.4.3 | 0.4.2 to 0.4.3 |
| `feat:` | 1.5.0 | 0.4.2 to 0.5.0 |
| `feat!:`, `fix!:` or a `BREAKING CHANGE:` footer | 2.0.0 | 0.4.2 to 0.5.0 |
| `docs`, `chore`, `ci`, `test`, `refactor`, `build` | none | none |

Dropping a runtime version (Java, Node, Python) forces consumers to act, so it carries `!`.
A `Release-As: 2.0.0` footer in a commit body sets the next version by hand.

## Files to copy

| Kit file | Destination in the consuming repo |
| --- | --- |
| `caller-release.yml` | `.github/workflows/release.yml`; set the shared repo SHA and the publish steps |
| `pr-lint.yml` | `.github/workflows/pr-lint.yml`; list your scopes if you want them enforced |
| `release-please-config.<stack>.json` | `release-please-config.json` |
| `release-manifest.json` | `.release-please-manifest.json` |
| `../pull_request_template.md` | `.github/pull_request_template.md`; replace the marketplace checklist lines |
| `../../CONTRIBUTING.md` sections on branches and commits | your `CONTRIBUTING.md` |

Stacks: `node` (Angular and other npm packages, also updates `package-lock.json`), `maven` (Spring Boot), `python`, and `monorepo` (a Maven backend plus a Node frontend in one repo).
The Python config also bumps the project's entry in `uv.lock`; replace `your-package` with the `name` from `pyproject.toml`.
Maven opens a follow-up PR that moves `pom.xml` to the next `-SNAPSHOT` version; add `"skip-snapshot": true` if you do not want it.

## Publish steps per stack

Put these in the caller's `publish` job, after the checkout of the tag.

| Stack | Steps |
| --- | --- |
| Maven | `actions/setup-java` with `cache: maven`, then `mvn -B -ntp deploy` with registry credentials from the `production` environment |
| Node | `actions/setup-node` with `registry-url`, then `npm ci`, `npm run build`, `npm publish --provenance` |
| Python | `astral-sh/setup-uv`, then `uv build` and `uv publish` with PyPI trusted publishing (OIDC, no stored token) |
| Any | `actions/attest-build-provenance` on the built files, and `gh release upload "$TAG" dist/*` to attach them |

## Seeding the version

The manifest holds the version released today.
For a new repo, keep `"0.0.0"` and set the first release with a `Release-As: 0.1.0` (or `1.0.0`) footer.
For an existing repo, set the manifest to today's version and push a tag `v<version>` on the commit that shipped it.
Add `"bootstrap-sha": "<that commit>"` to the config when no such tag exists, so release-please skips older history.

## Hotfixes

1. Branch from the released tag: `git switch -c release/1.4.x v1.4.2` and push it.
2. Merge `fix:` PRs into `release/1.4.x`. A `feat:` there would bump the minor version, so keep it to fixes.
3. The push runs the caller on `release/1.4.x`. The reusable workflow passes `target-branch: release/1.4.x`, so the patch release PR targets that branch.
4. Merge it to tag `v1.4.3`, then cherry-pick the fix to `main` with the same title.

A multi-package repo names the line after the component: `release/backend-1.4.x`.

## Repository settings

- Settings, General, Pull Requests: allow squash merge only, with "Default to pull request title".
- Settings, General: turn on "Automatically delete head branches".
- Settings, Rules: protect `main` and `release/**` with required PR review (CODEOWNERS), the `CI` and `PR lint` checks, linear history and no force pushes.
- Settings, Actions, General: allow GitHub Actions to create pull requests, for the `GITHUB_TOKEN` fallback.
- Settings, Environments: create `production` with required reviewers and the registry secrets.

## Tokens

The release PR and tag created with `GITHUB_TOKEN` start no other workflow, so required CI checks never report on the release PR.
Three options, in order of preference:

1. A GitHub App with Contents, Issues and Pull requests write. Set the variable `RELEASE_APP_CLIENT_ID` and the secret `RELEASE_APP_PRIVATE_KEY`; the reusable workflow mints a one-hour token.
2. A fine-grained PAT with the same permissions in the secret `RELEASE_TOKEN`.
3. Neither: release-please uses `GITHUB_TOKEN`, and an admin merges the release PR past the missing checks.

## What changed from the first draft of this kit

- Hotfix release PRs now target the pushed `release/**` branch. release-please targets the default branch unless `target-branch` is set.
- The job has `issues: write`, which release-please needs to create its `autorelease` labels.
- The reusable workflow exposes `releases_created`, `paths_released` and every output as `all`, so multi-package repos can publish per package.
- Actions are pinned to full commit SHAs: release-please-action v5.0.0, checkout v7.0.1, create-github-app-token v3.3.0, action-semantic-pull-request v6.1.1.
- Workflow permissions default to none, and each job asks only for what it uses. Runs on one branch never overlap.
- Configs hide `docs`, `chore`, `ci`, `test`, `refactor` and `build` commits from the changelog and add a Performance section.
- The PR lint also checks the branch name and rejects a capitalised subject or a trailing period.

## References

- release-please: https://github.com/googleapis/release-please
- release-please-action: https://github.com/googleapis/release-please-action
- Conventional Commits: https://www.conventionalcommits.org
- Semantic Versioning: https://semver.org
