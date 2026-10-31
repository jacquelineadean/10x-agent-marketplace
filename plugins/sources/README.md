# sources

Read-only access to company systems for the plugins that present data. A gatherer subagent
reads GitHub, Jira, Confluence, Datadog, PagerDuty, ServiceNow, Databricks, Postgres and
Oracle through the session's connectors and writes three files to a run folder:

| File | Holds |
| --- | --- |
| `facts.json` | every number by system (`github`, `jira`), each record with its source and note |
| `queries.json` | the query behind each fact: system, lane, connection, query text, window, as-of date |
| `digest.md` | fact values, series ranges and derived targets under 12,000 bytes, for Claude to read |

Raw tool output stays inside the subagent. Built under
[RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md) and
[spec 002](../../specs/002-chronicle-split/spec.md).

## Use
- Skills that need company numbers, such as `chronicle:story`, call `sources:gatherer`.
  When a request names no system, they ask its `Mode: status` and show a picker of the nine
  systems with each one's status.
- `/sources:connect [system] [--agent]` sets up a system: a connector, keys for the script
  collectors (sources 0.2.0), a named connection, or a user-level database agent.

## Command line
```bash
plugins/sources/scripts/sources detect --connectors github,claude_ai_Atlassian
plugins/sources/scripts/sources detect --picker      # AskUserQuestion questions as JSON
plugins/sources/scripts/sources check RUN_FOLDER     # facts.json against queries.json
plugins/sources/scripts/sources digest RUN_FOLDER    # check, then write digest.md
plugins/sources/scripts/sources connection add warehouse --system postgres --host db:5432 \
  --database analytics --env user=PGUSER --env password=PGPASSWORD
plugins/sources/scripts/sources agent --connection warehouse
```

## Files
| Path | Holds |
| --- | --- |
| `agents/gatherer.md` | the subagent: `status`, `gather` and `digest` modes |
| `skills/connect/` | `/sources:connect`, run only by the user (`disable-model-invocation`) |
| `recipes/` | one recipe per system: how to reach it, what to read, what never to do |
| `references/facts.md` | a link to the engine's facts file reference |
| `scripts/sources` | launcher used through `${CLAUDE_PLUGIN_ROOT}` |
| `src/sources` | a link to `packages/sources/src/sources`; Claude Code copies linked files at install |

## Privacy
Nothing leaves the machine except the queries the connectors run. `connections.json` holds
hosts and variable names, never a key. The plugin bundles no MCP server.
