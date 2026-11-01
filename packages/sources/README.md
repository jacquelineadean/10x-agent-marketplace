# sources (package)

The read-only data code the data plugins share: which systems a session can reach, the
source picker, named connections, the facts and queries contract, the digest, the
user-level database agent, and the script-lane collectors with their HTTPS transport and
SQL guard. Standard library only; Postgres and Oracle run through the user's own `psql` and
SQLcl. It imports neither the chronicle engine nor a plugin. Decided in
[RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md); built under
[spec 002](../../specs/002-chronicle-split/spec.md).

## How a plugin uses it
A plugin links the package into its own source folder,
`plugins/<name>/src/sources -> ../../../packages/sources/src/sources`, and runs
`python -m sources` from its launcher or imports it. Claude Code copies linked files at
install. sources, briefing, blueprint and impact-review link it.

## The script lane
`sources gather RUN` runs every `queries.json` entry with `"lane": "script"`: its
`request` goes to the system's collector, the result lands at the entry's path in
`facts.json`, and the entry gets the query as run and its as-of date. `--roll` moves each
window to end with the last complete period, as `briefing refresh` does.

| Guard | Where |
| --- | --- |
| HTTPS only; GET, plus POST to named read-only paths (Jira's count, Datadog's RUM aggregate, Databricks statements) | `connectors/http.py` |
| One `SELECT` or `WITH` statement, no write keyword, no function with side effects, named parameters only | `core/sql.py` |
| Read-only session: `default_transaction_read_only` (Postgres), `SET TRANSACTION READ ONLY` (Oracle), a read-only principal (Databricks) | `connectors/postgres.py`, `connectors/oracle.py` |
| 30-second statement limit, 10,000-row cap, argument lists and never a shell | each SQL collector |
| Keys from environment variables only; passwords never in an argument list or a message | `core/reach.py`, `config/settings.py` |

## Layout
| Folder | Holds |
| --- | --- |
| `core/` | systems and picker groups, detection, the picker, named connections, the facts and queries contract, the digest, the database agent, periods and rolled windows, the SQL guard, where a collector reads (`reach.py`), results (`collect.py`) and the gather bookkeeping |
| `connectors/` | the HTTPS transport and its errors; one collector per system (`github/` with the GitHub transport moved from impact-review, `atlassian.py`, `datadog.py`, `pagerduty.py`, `servicenow.py`, `databricks.py`, `postgres.py`, `oracle.py`); `wire.py`, the network and programs a collector touches; JSON and Markdown files; which programs are on `PATH` |
| `entrypoints/cli/` | `detect`, `gather`, `check`, `digest`, `connection`, `agent` |
| `config/` | the only environment reads |

## Tests
`uv run pytest packages/sources/tests` from the repository root. Collectors run against
recorded replies under `tests/fixtures/` and fake programs; no test calls a system.
