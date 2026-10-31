# chronicle-engine

The engine the chronicle plugins share: facts and the derive table, the story model and page renderer, theme
tokens, the animation clock and stage, the diagram kind, every export, and the command line. It names no plugin.
Decided in [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md); built under
[spec 002](../../specs/002-chronicle-split/spec.md).

## How a plugin uses it
1. The plugin links this package into its own source folder:
   `plugins/<name>/src/chronicle_engine -> ../../../packages/chronicle-engine/src/chronicle_engine`.
   Claude Code copies linked files into its plugin cache at install, so each plugin installs alone and git holds
   one copy.
2. The plugin's `pack` module fills `chronicle_engine.registry`: block types (`add_block`), an art provider
   (`set_art`), animation kinds (`add_kind`), theme policies (`POLICIES`), commands (`COMMANDS`), asset folders
   (`add_asset_root`) and defaults (`DEFAULTS`).
3. The plugin's `__main__` imports the pack, then runs `chronicle_engine.entrypoints.cli.main.main()`.

`python -m chronicle_engine` runs the engine with no plugin: stories without art, and the `diagram` animation kind.

## Layout

| Folder | Holds |
| --- | --- |
| `registry.py` | the extension points above |
| `core/story/` | facts, derive, story checks, theme tokens and fonts, diagram sanitizer, renderer and neutral blocks |
| `core/motion/` | the step clock, CSS keyframe timeline, stage, diagram kind, HTML figure, frame times and GIF encoder |
| `connectors/` | files (JSON, HTML, images, asset parts across roots), a local Chromium for screenshots and frames, ffmpeg and OpenCV video |
| `entrypoints/cli/` | `new`, `check`, `build`, `shoot`, `animate new/check/build`, and `paint` when a plugin brings art |
| `assets/` | the page stylesheet and runtime script in numbered parts, the stage and diagram stylesheets, `fonts.json` |

## Tests
`uv run pytest packages/chronicle-engine/tests` from the repository root. The command-line tests run the engine in
a separate process with only this package importable, so no plugin's registrations apply.
