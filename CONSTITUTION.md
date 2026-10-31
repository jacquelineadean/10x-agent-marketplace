# 10x-agent-marketplace — Constitution

> The non-negotiable rules. Every RFC, spec and pull request is checked against this. If a
> change conflicts with it, stop and say so — amend it deliberately instead of working around it.
> Keep it short: a rule that cannot be checked is a wish.

**Version:** 1.1.0 · **Ratified:** 2026-10-07 · **Amended:** 2026-10-31

## Principles
1. **Scripts compute, Claude writes.** API calls, counting and math run in plugin code. Claude reads only compact outputs such as a digest, never raw API responses.
2. **Every number has a source.** Each metric in generated text maps to a field in the run's `metrics.json`. Claims with no source are written as a placeholder for the user to fill.
3. **Local and private by default.** Collected data stays on the user's machine. Plugins make no network calls except to the data source being read. Amendment 1 allows a publish the user confirms.
4. **Read-only against sources.** Plugins never create, edit or delete anything in GitHub or any other source system.
5. **One plugin, one job.** Each plugin lives in its own `plugins/<name>/` folder with its own version and README.

## Guardrails (things that must never happen)
- Never commit a run folder, raw API data, a token or a `.env` file.
- Never print or log a token, an `Authorization` header or a full request URL with a token.
- Never send collected data to a third-party service, including an MCP server, from plugin code, except a publish the user confirms under amendment 1.
- Never call a write endpoint (POST/PATCH/PUT/DELETE mutations) on a source system; GraphQL calls are queries only.
- Never add a runtime dependency to a plugin without an approved RFC.

## Quality gates (what "done" means)
- `groundwork.py verify` passes: ruff format, ruff lint, mypy strict, pytest.
- Each acceptance criterion in the spec has a test or a written manual check.
- Tests use recorded GitHub responses; no test calls a live API.
- The plugin README states install steps, required token scopes and a manual test.

## Amendments
1. **User-confirmed publishing** (2026-10-31, RFC-0007 answer 14, approved by Jacqueline Dean). A publish to a
   destination the user names, such as a claude.ai Artifact, Google Drive or Microsoft 365, is allowed after the user
   confirms that publish. It settles RFC-0002 open question 4 for Artifacts and allows RFC-0007's `--to google` and
   `--to microsoft`.
