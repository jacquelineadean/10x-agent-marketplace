# contributing

Two skills that make GitHub contributions fast to review: pull request descriptions a
reviewer can approve on the first pass, and branch names and commit messages that release
tools can read. Both read the repo's own rules first (PR template, CONTRIBUTING.md, PR
lint workflow, commitlint config) and fall back to their defaults only where the repo is
silent.

Markdown only: no scripts, no dependencies, no network calls of its own.

## Install
```
/plugin marketplace add jacquelineadean/10x-agent-marketplace
/plugin install contributing@10x-agent-marketplace
```

## Skills
| Skill | Triggers on | What it does |
| --- | --- | --- |
| `/contributing:pull-request` | opening, drafting or updating a PR; "write the PR description"; "add screenshots" | Gathers facts from `git log` and `git diff`, writes a Conventional Commit title and a body in the repo's template (or the bundled one), adds Playwright screenshots, videos or GIFs for visible changes, and opens the PR as a draft with `gh` or the GitHub MCP server |
| `/contributing:branch-and-commit` | creating a branch, committing, rebasing, "clean up my commits" | Names the branch `<type>/<slug>` or `<type>/<issue>-<slug>`, writes Conventional Commit messages with scopes, bodies and `BREAKING CHANGE:` footers, keeps commits atomic and pushes rewrites with `--force-with-lease` |

## Bundled references
Loaded only when the skill needs them:

| File | Holds |
| --- | --- |
| `skills/pull-request/references/pr-template.md` | Default PR template: summary, why, changes, screenshots, how to test, dependencies and rollout, risks, how to review, references, checklist; plus a small-PR variant |
| `skills/pull-request/references/github-formatting.md` | GitHub advanced formatting: collapsed sections, alerts, tables, diff and suggestion blocks, Mermaid, images and `<picture>`, attaching files and their size limits, autolinks, closing keywords, permalinks, task lists, footnotes, render preview |
| `skills/pull-request/references/media.md` | What to capture per kind of change, a Playwright capture script, before shots from a worktree, WebM to MP4 and GIF with ffmpeg, the two routes into a PR (drag and drop, or a media branch linked by SHA), privacy |

## Writes to GitHub
The pull-request skill pushes the branch and opens a draft PR only when you ask for a PR.
It never merges, approves or pushes to a branch you did not create. Screenshots go into
the repo (on a separate `pr-media/<slug>` branch) only after you agree; by default it
saves them locally and tells you where to drag each one.

Token scopes: branches, commits and messages need none. Opening a PR or pushing a media
branch needs `gh auth login`, or a GitHub MCP token, with `repo` (classic token) or
Contents and Pull requests read and write (fine-grained token).

## Manual test
1. On a branch with a UI change, run `/contributing:pull-request`.
2. Expect: a title such as `feat(settings): add save button`, a body that follows
   `.github/pull_request_template.md` if the repo has one, before and after screenshots
   or placeholders naming each file, exact test commands, and a draft PR link.
3. Run `/contributing:branch-and-commit` with "commit this as a fix for #42".
4. Expect: a `fix/42-<slug>` branch if you are on the default branch, and a
   `fix(<scope>): <subject>` commit with a body and `Closes #42`.
