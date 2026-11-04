<!--
Title: a Conventional Commit, e.g. "feat(chronicle): add a timeline block".
The title becomes the squash commit and the CHANGELOG line. Add "!" after the type for a breaking change.
-->

## Summary

<!-- What changes for a user of the plugin, in one to three sentences. -->

## Decision and spec

- RFC: <!-- DECISIONS/RFC-NNNN-slug.md, or "none: no behaviour change" -->
- Spec: <!-- specs/NNN-slug/ updated in this PR when behaviour changes -->
- Closes: <!-- #issue -->

## Release impact

- [ ] `feat`: new skill, command or option (minor bump)
- [ ] `fix` or `perf`: behaviour fix (patch bump)
- [ ] Breaking (`!` in the title, plus a `BREAKING CHANGE:` footer saying what users must do)
- [ ] No release: docs, tests, CI or chores only

## Checklist

- [ ] ruff format, ruff check, mypy and pytest pass (AGENTS.md, Commands)
- [ ] `claude plugin validate .` passes
- [ ] Each acceptance criterion has a test or a written manual check
- [ ] Tests use recorded responses under `tests/fixtures/`; none calls a live API
- [ ] No run folder, raw API data, token or `.env` file is committed
- [ ] README, ARCHITECTURE.md and CODEMAP.md updated where this changes them
- [ ] `version` fields left alone: release-please bumps them

## Manual test

<!-- The commands you ran in Claude Code and what you saw. -->
