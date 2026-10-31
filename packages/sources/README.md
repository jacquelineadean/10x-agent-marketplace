# sources (package)

The read-only data code the data plugins share: which systems a session can reach, the
source picker, named connections, the facts and queries contract, the digest and the
user-level database agent. Standard library only. It imports neither the chronicle engine
nor a plugin. Decided in [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md);
built under [spec 002](../../specs/002-chronicle-split/spec.md).

## How a plugin uses it
A plugin links the package into its own source folder,
`plugins/<name>/src/sources -> ../../../packages/sources/src/sources`, and runs
`python -m sources` from its launcher. Claude Code copies linked files at install.
The sources plugin links it today; briefing and blueprint link it when they ship.

## Layout
| Folder | Holds |
| --- | --- |
| `core/` | systems and picker groups, detection, the picker, named connections, the facts and queries contract, the digest, the database agent |
| `connectors/` | JSON and Markdown files; which programs are on `PATH` |
| `entrypoints/cli/` | `detect`, `check`, `digest`, `connection`, `agent` |
| `config/` | the only environment reads: which key names are set, never their values |

## Tests
`uv run pytest packages/sources/tests` from the repository root. No test calls a system.
