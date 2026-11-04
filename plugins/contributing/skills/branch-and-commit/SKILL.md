---
name: branch-and-commit
description: Name git branches and write commit messages that follow the repo's conventions, defaulting to `<type>/<slug>` branches and Conventional Commits with semver-aware types, scopes, breaking-change footers and issue links. Also covers atomic commits, fixups, rebasing safely and what never to commit. Use whenever you create a branch, commit, amend, squash, rebase or push, write or fix a commit message, pick a branch name for a feature or fix, or the user says "commit this", "make a branch", "clean up my commits" or "what should I call this branch", even for a one-line change.
---

# Branches and commits

Branch names tell CI, reviewers and release tools what kind of change is coming. Commit
messages are the only documentation that travels with every line of code (`git blame`,
`git log`), and release tools such as release-please and semantic-release read them to
pick the next version and write the changelog.

## 1. Read the repo's rules first

The repo's conventions beat these defaults. Check, in order: `CONTRIBUTING.md`,
`AGENTS.md` or `CLAUDE.md`, PR lint workflows in `.github/workflows/` (branch patterns,
allowed types and scopes), commitlint config (`commitlint.config.*`, `.commitlintrc*`),
and `git log --oneline -20` for the style in use. A session or tool that assigns a branch
name (for example `claude/<slug>`) wins over everything here.

## 2. Branch names

Default pattern: `<type>/<slug>`, or `<type>/<issue>-<slug>` when an issue exists.

| Branch | Use |
| --- | --- |
| `feat/search-filters` | New feature |
| `fix/412-pagination-off-by-one` | Bug fix for issue 412 |
| `docs/contributing-guide` | Docs only |
| `refactor/extract-auth-client` | No behaviour change |
| `chore/bump-eslint-9` | Tooling, dependencies |
| `release/2.4.x` | Hotfix line cut from a release tag |

Rules:
- `<type>` is one of the commit types in section 3, so the branch predicts the PR title.
- Slug: lower case, `a-z`, `0-9` and `-`, 2 to 5 words, under about 50 characters in all.
  Name the change ("search-filters"), never the person or the date.
- Branch from the latest default branch: `git fetch origin && git switch -c feat/x origin/main`.
- One branch per change. Start a new branch for unrelated work found along the way.
- Delete the branch after merge.

## 3. Commit messages

Default format: [Conventional Commits 1.0](https://www.conventionalcommits.org/en/v1.0.0/).

```text
<type>(<scope>)!: <subject>

<body: what changed and why, wrapped at 72 columns>

<footers>
```

| Type | Use | Semver |
| --- | --- | --- |
| `feat` | New capability for users | minor |
| `fix` | Wrong behaviour corrected | patch |
| `perf` | Faster, same behaviour | patch |
| `revert` | Reverts an earlier commit | patch |
| `refactor` | Code change, same behaviour | none |
| `docs` | Documentation only | none |
| `test` | Tests only | none |
| `build` | Build system, dependencies | none |
| `ci` | CI configuration | none |
| `chore` | Anything else with no user effect | none |
| `style` | Formatting only, if the repo uses it | none |

Subject line:
- Imperative mood, as if completing "This commit will ...": "add", "fix", "remove".
- Lower case first word unless the repo says otherwise, no trailing period.
- Header (type, scope and subject) at most 72 characters; 50 is better.
- Scope is the module, package or plugin touched: `fix(parser): ...`. Use the repo's list.

Body (skip it only for changes that explain themselves, such as a typo):
- Say why the change was needed and what it does differently. The diff already shows how.
- Name the symptom for a fix ("Requests over 1 MB failed with 413") and the cause.
- Wrap at 72 columns. Lists with `-` are fine.

Footers, one per line after a blank line:
- `BREAKING CHANGE: <what users must do>` with `!` in the header. Renaming or removing a
  public flag, API, file or config key is breaking.
- `Closes #123` or `Refs #123` to link an issue.
- `Co-authored-by: Name <email>` for pair work.
- Any trailers the repo or session asks for, verbatim and last.

Examples:

```text
feat(search): add date range filter

Users asked for results from a single sprint. The filter maps to the
existing `created` index, so queries stay under 50 ms on 1M rows.

Closes #208
```

```text
fix(api)!: return 404 for unknown project ids

Unknown ids returned 200 with an empty body, which clients cached as
"no data". They now return 404.

BREAKING CHANGE: clients that treated an empty 200 as "not found" must
handle 404 instead.
```

Write a multi-line message with a heredoc so the shell keeps the line breaks:

```bash
git commit -F - <<'EOF'
fix(parser): accept trailing commas in arrays

The JSON5 inputs from the CLI include trailing commas.
EOF
```

## 4. Shaping commits

- One logical change per commit: each commit builds and passes tests on its own. This
  keeps `git bisect` and `git revert` useful.
- Separate a refactor from the behaviour change it enables: two commits, refactor first.
- Stage on purpose: `git add -p` or named paths, then `git diff --staged` before committing.
  `git add -A` sweeps in stray files.
- Fix an earlier commit on your branch with `git commit --fixup <sha>`, then fold fixups in
  before review with `GIT_SEQUENCE_EDITOR=: git rebase -i --autosquash origin/main`
  (the variable skips the editor, for environments with no interactive terminal).
- In a squash-merge repo, the PR title becomes the commit on the default branch. Branch
  commits still need clear messages for reviewers, but the title matters most.

## 5. Rewriting and pushing

- Rewrite only your own unshared branch. After someone reviews or builds on it, add
  commits instead, unless the repo asks for a cleaned history.
- After a rebase or amend, push with `git push --force-with-lease`. It refuses to overwrite
  commits you have not seen. Never force-push the default branch or someone else's branch.
- Keep the branch current with `git fetch origin && git rebase origin/main`, or merge the
  base if the repo prefers merge commits or the branch is shared.
- Sign commits (`git commit -S`) when branch protection requires signatures.

## 6. Never commit

- Secrets: tokens, keys, passwords, `.env` files, credentials in config or test fixtures.
  If one lands in a commit, rotating it is the fix. Rewriting history does not unpublish it.
- Generated output: build folders, coverage, caches, local run data, editor settings.
  Add them to `.gitignore` instead.
- Large binaries without the repo's LFS setup.
- Unrelated formatting churn across files the change does not touch.
- Hand edits to files a tool owns, such as lockfiles, generated changelogs or version
  fields that a release bot bumps.
