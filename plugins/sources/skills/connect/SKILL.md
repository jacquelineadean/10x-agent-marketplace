---
name: connect
description: Set up a company system for the sources gatherer, by connector, keys, a named connection or the user-level database agent.
disable-model-invocation: true
argument-hint: "[system] [--agent]"
---

# Connect a system

Sets up one of the nine systems the gatherer reads: GitHub, Jira, Confluence, Datadog,
PagerDuty, ServiceNow, Databricks, Postgres and Oracle. Never ask for a key in the chat and
never write one to a file. Keys live in the user's shell environment or secret manager.

## 1. See what is set up
Run `"${CLAUDE_PLUGIN_ROOT}/scripts/sources" detect --connectors <names>`, where `<names>`
lists the MCP server names in your tool list (between `mcp__` and the next `__`),
comma-separated. Show the nine lines. When `$ARGUMENTS` names no system, ask which to set up
with one AskUserQuestion.

## 2. Pick a lane
Read `${CLAUDE_PLUGIN_ROOT}/recipes/<system>.md`. Its "Reach" section names both lanes.

- **Connector.** The gatherer reads through it on claude.ai, in Cowork and in Claude Code.
  Add the system's connector in claude.ai (Settings, Connectors) or with
  `claude mcp add --scope user`, following the vendor's instructions. Prefer a read-only
  token or role. A plugin never bundles the server, so it starts only where the user adds it.
- **Keys.** The script collectors read the variables the recipe names, in Claude Code on the
  user's machine. Tell the user to export them in their shell profile or secret manager.
  Postgres needs `psql` installed and Oracle needs SQLcl (`sql`).
- **Named connection.** For a database or a self-hosted system, record its host and the
  names of the variables that hold its keys:
  `"${CLAUDE_PLUGIN_ROOT}/scripts/sources" connection add warehouse --system postgres --host db.internal:5432 --database analytics --env user=PGUSER --env password=PGPASSWORD`.
  The file (`~/.config/sources/connections.json`, or `$SOURCES_CONNECTIONS`) holds no secret,
  and the command refuses a value that is not a variable name.

## 3. The database agent (`--agent`)
Plugin agents cannot start MCP servers. A user-level agent can, and its servers start only
inside it. For Postgres, Oracle and Databricks connections with no connector in the session:
1. Name each database with `connection add` first.
2. Tell the user that `~/.claude/agents/sources-db.md` will hold one server per connection:
   Postgres through `uvx postgres-mcp --access-mode=restricted` with the connection's
   `PGUSER` and `PGPASSWORD` variables; Oracle through SQLcl's `sql -mcp` with a SQLcl saved
   connection of the same name (`conn -save <name> -savepwd ...` in SQLcl); Databricks through
   the workspace's managed SQL server with a token from the connection's `token` variable.
3. After the user confirms, run
   `"${CLAUDE_PLUGIN_ROOT}/scripts/sources" agent --connection <name> ...`, and ask the user
   to restart Claude Code so the agent loads.
4. Pages then call the `sources-db` agent for those databases, and `sources:gatherer` with
   `Mode: digest` after it.

## 4. Confirm
Run `detect` again and show the system's line: `script collector ready` means
`sources gather` can read it.

## Rules
- Read only: suggest read-only tokens, roles and database users.
- Never print, echo or store a key; check a variable with `detect`, which reports only
  whether it is set.
