# Spec 002: chronicle split into four plugins on one engine

Source: [RFC-0007](../../DECISIONS/RFC-0007-chronicle-two-branches.md), revision 3. Built ahead of approval at the
owner's request (31 Oct 2026), as for RFC-0002 to RFC-0006.
Each acceptance criterion names the test that checks it or a manual check. The work lands as a stack of draft
pull requests, each based on the one before; the first is based on the RFC's own pull request.

| PR | Branch | Phase | Releases |
| --- | --- | --- | --- |
| 1a | `claude/rfc7-1-engine` | 1: engine extraction, Python side | chronicle 0.5.0 |
| 1b | `claude/rfc7-1b-assets` | 1: page parts, chrome registries, vocabulary lint | chronicle 0.5.1 |
| 2 | `claude/rfc7-2-sources` | 2: sources plugin, chronicle researcher | sources 0.1.0, chronicle 0.6.0 |
| 3 | `claude/rfc7-3-briefing` | 3: briefing, brand kit | briefing 0.1.0 |
| 4 | `claude/rfc7-4-blueprint` | 4: blueprint, TAD move, interactive figures | blueprint 0.1.0, chronicle 0.7.0 |
| 5 | `claude/rfc7-5-collectors` | 5: script-lane collectors, refresh, impact-review on sources | sources 0.2.0, briefing 0.2.0 |
| 6 | `claude/rfc7-6-creative` | 6: creative additions | chronicle 0.8.0 |

## Design decisions that refine the RFC
- **Registries.** `chronicle_engine.registry` holds block types, the art provider, page chrome (progress devices,
  chapter marks, stat skins, plate frames), animation kinds, theme policies, CLI commands and asset roots. A
  plugin's `pack` module fills them on import; its `__main__` imports the pack and runs the engine CLI.
- **The page layout stays in the engine** with neutral chrome: progress `steps`, marks `label`, `plain`, `step` and
  `none`, stats `rule` and `cards`, frame `none`, track lines `solid` and `dashed`. chronicle registers the
  creative chrome: progress `arches`, `track`, `route`, `tape`, `flags` and `clock`, track lines `belt`, `road` and
  `rail`, marks `arch`, `tag`, `sign`, `badge`, `flag`, stats `receipt` and `ticket`, frames `mat` and `tape`. A
  plugin's pack sets its defaults, so a chronicle page with no theme looks as it does today. The progress icons stay
  in the engine, because flow figures and widgets draw them too.
- **Art is a provider.** A story's `art`, `hero.art`, `chapters[].art` and the `plate` block need the art provider.
  chronicle registers the painter as that provider; another plugin's build refuses `art` with a message.
- **The SVG reader stays in chronicle.** Only the painter and the scene kind read drawings, so `parse.py` and
  `pathdata.py` stay beside the painter (the RFC's table listed them under the engine).
- **Page parts.** A page ships the engine's always-parts (base, page and neutral identity CSS; core, progress and
  boot scripts) plus the parts of each figure type on it: charts, figures (stats, scrolly, timeline, stepper,
  compare, matrix, roadmap, team, model), explainers (tilemap, flow, diagram), lessons (quiz, checklist, widget)
  and the drawn-figure CSS (diagram, plate). `14-page.css`, the page layout and the neutral figure styles, ships
  with every page: its rules use shared class names (`.seg`, `.card`, `.tile`, `.step`) that widgets may also
  render, so splitting it could change a widget's look. chronicle adds its chrome parts to every page and its plate
  parts to pages with art.
- **The split keeps the cascade.** CSS moved between files so the joined order stays the same, except where neutral
  and creative rules swapped places inside the identity stylesheet; those rules style different elements. Every
  element's computed style is compared between the 1a and 1b builds to prove it.
- **Stable output.** The diagram kind ordered its pulse tracks by Python's per-run string hashing, so the same
  animation could build to two different files. It now uses first-appearance order.
- **Tests.** Existing chronicle tests stay with chronicle, because they test chronicle's behavior through the
  engine. Engine-only tests live in `packages/chronicle-engine/tests/` with `test_engine_*.py` names.

## Acceptance criteria

### PR 1a: engine extraction (behavior unchanged)
| ID | Criterion | Check |
| --- | --- | --- |
| AC-1 | `packages/chronicle-engine/src/chronicle_engine/` holds facts, derive, the story model and renderer, theme tokens, the motion clock and stage, the diagram kind, the SVG reader, the files, browser and video connectors, and the engine CLI | `test_engine_boundary.py::test_engine_modules_exist` |
| AC-2 | `plugins/chronicle/src/chronicle_engine` is a symlink to that package, and a local marketplace install copies real files | `test_engine_boundary.py::test_chronicle_links_the_engine`; manual check M-1 |
| AC-3 | The engine imports no plugin package | `test_engine_boundary.py::test_engine_imports_no_plugin` |
| AC-4 | The engine CLI runs with no pack: `check` and `build` work for a story without art, and refuse `art` with a message | `test_engine_cli.py` |
| AC-5 | Every bundled example and the docs pages build byte-for-byte as before: 57 files compared at a fixed `PYTHONHASHSEED` (the 4 `publish-files.json` hold absolute paths), and the outputs no longer depend on the hash seed | build comparison recorded in the PR; `plugins/chronicle/tests/test_pack.py` |
| AC-6 | The sameness review runs only through chronicle's `distinct` policy | `plugins/chronicle/tests/test_theme.py` |
| AC-7 | The four quality gates pass; chronicle is 0.5.0 in both manifests | CI and `claude plugin validate .` |

### PR 1b: page parts and chrome registries
| ID | Criterion | Check |
| --- | --- | --- |
| AC-8 | The page runtime starts figures through a registry, so a page without a block's part still starts | `test_engine_pages.py` and browser check M-2 |
| AC-9 | A page ships only the CSS and script parts its blocks and chrome use | `test_engine_pages.py::test_parts_follow_blocks` |
| AC-10 | Creative chrome comes from chronicle's registrations; the engine alone offers the neutral chrome | `test_engine_pages.py::test_engine_chrome_is_neutral`, `plugins/chronicle/tests/test_theme.py` |
| AC-11 | No engine file uses a plugin word: watercolor, plate, sameness, KPI, SQL, Datadog | `test_engine_boundary.py::test_engine_vocabulary` |
| AC-12 | Every example page loads in Chromium with no script error and starts every figure | browser check M-2, recorded in the PR |
| AC-13 | Pages render as in 1a: the same markup outside the runtime, and the same computed style for every element and pseudo-element in seven browser modes, for the 4 example pages and 14 theme variants that use the chrome the examples leave out | browser check M-4, recorded in the PR |
| AC-14 | The four quality gates pass; chronicle is 0.5.1 in both manifests | CI and `claude plugin validate .` |

### PR 2 to PR 6
Criteria for later pull requests are added to this spec in the pull request that builds them.

## Manual checks
- **M-1.** Install chronicle from a local marketplace into a scratch `CLAUDE_CONFIG_DIR` and confirm the cache holds
  `src/chronicle_engine/` as real files.
- **M-2.** Load every example page in headless Chromium at 1280 pixels; record script errors (none allowed) and the
  count of started figures.
- **M-3.** RFC-0007 phase 0 items that need other hosts: install on claude.ai, in Cowork and on a Windows checkout;
  run a user-level gatherer with inline `mcpServers`; create a file through the Google Drive and Microsoft 365
  connectors. These cannot run in the build container and stay open.
- **M-4.** Build every example and 14 quarterly variants (progress `arches`, `tape`, `flags`, `clock`; track lines
  `solid`, `road`, `rail`; marks `arch`, `sign`, `flag`, `step`, `none`; stats `rule`; frame `none`) with 1a and 1b
  at `PYTHONHASHSEED=11`. Compare the markup outside the runtime, then load each pair in Chromium with a frozen page
  clock in seven modes (desktop light, dark, attribute dark, reduced motion, forced colors; phone light and dark), at
  the top and the middle of the page, and compare the DOM and every computed style. Wall-clock motion (painted
  layers, flow tokens) is parked before each snapshot; a mode that differs is re-run three times.
