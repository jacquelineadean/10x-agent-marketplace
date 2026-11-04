# Default pull request template

Use this when the repo has no template of its own. Copy the block below, fill it in, and
delete a whole section only when it cannot apply (for example Screenshots on a backend-only
change). Keep the HTML comments out of the final body: they are hints for the writer.

A repo can adopt this file as `.github/pull_request_template.md`; GitHub then pre-fills
every new PR with it.

````markdown
## Summary

<!-- One to three sentences: what changes for a user, caller or operator. -->

Closes #<issue>

## Why

<!-- The problem and its evidence: issue, incident, metric, user report. Link it. -->

<details>
<summary>Background</summary>

<!-- Longer context, alternatives considered and why they lost. -->

</details>

## Changes

<!-- Grouped by area. Name files or modules so the reviewer can find them. -->

- **API**: ...
- **UI**: ...
- **Tests**: ...

## Screenshots and recordings

<!-- Anything visible. Before and after side by side. Delete for non-visual changes. -->

| Before | After |
| --- | --- |
| <img src="..." width="400" alt="Settings page before: no save button"> | <img src="..." width="400" alt="Settings page after: save button at top right"> |

<details>
<summary>Recording: saving a profile (12 s)</summary>

<!-- Drag the .mp4 or .gif here, or link a committed file. -->

</details>

## How to test

<!-- Exact steps a reviewer can paste, with the expected result of each. -->

```bash
npm ci
npm test -- profile
```

1. Run `npm run dev` and open `http://localhost:3000/settings`.
2. Change the display name and press **Save**.
3. Expect a "Saved" toast and the new name in the header.

Automated: <!-- e.g. "14 new tests in tests/profile.test.ts; full suite 312 passed". -->

## Dependencies and rollout

<!-- New or upgraded packages (and why), migrations, feature flags, config or env vars,
deploy order, PRs this depends on. Write "None" if none. -->

- Depends on: #<pr>
- Migration: ...
- Feature flag: ...

## Risks and rollback

<!-- What could break, how we would notice, how to undo. -->

> [!WARNING]
> <!-- Only for a real risk: data migration, breaking API, security-sensitive code. -->

## How to review

<!-- The file to start with, the part that needs the hardest look, what is mechanical. -->

1. Start with `src/...`: ...
2. `src/...` is a rename only.

## References

<!-- Issues, docs, designs, related PRs, permalinks to code, external docs. -->

- Design: ...
- Related: #<pr>

## Checklist

- [ ] Title follows the repo's commit convention
- [ ] Tests added or updated, and the full suite passes locally
- [ ] Lint, format and type checks pass
- [ ] Docs, README or changelog updated where behaviour changed
- [ ] Screenshots or recordings added for visible changes
- [ ] No secrets, credentials, personal data or generated files committed
- [ ] Breaking changes marked with `!` and a `BREAKING CHANGE:` footer
````

## Small PR variant

For a one-file fix or a dependency bump, three sections are enough:

````markdown
## Summary

Fix the off-by-one in `paginate()` that dropped the last item of every page. Closes #412

## How to test

`pytest tests/test_paginate.py` (3 new cases, all pass; fail on `main`).

## Checklist

- [x] Tests added
- [x] Lint and type checks pass
````
