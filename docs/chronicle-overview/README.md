# chronicle executive overview

Sources for the executive overview of the chronicle plugin, written for developers and IT
leadership. The page is built with chronicle from its own repository; every figure is in
`facts.json` with its source.

| Path | Holds |
| --- | --- |
| `story.json` | theme, hero and seven chapters: problem, uses, plugin, how it works, architecture, controls, status |
| `facts.json` | every figure: code size, tests, releases, RFC counts, build timings, with sources |
| `art/` | the hero and problem-chapter drawings, painted at build time |
| `diagrams/build.svg` | the stepped diagram of `chronicle build` |
| `diagrams/plugin.svg` | the plugin directory and what each file becomes in a session, after the Claude Code docs' plugin diagram |
| `plugin-diagram/animation.json` | the plugin diagram as a standalone animation: SVG, PNG and GIF |
| `widgets/tad-player.*` | plays the architecture animation inside the page, with a pause button |
| `tad/animation.json` | the architecture animation (TAD) at 16:9, for slides, GIF and MP4 |
| `tad/animation-page.json` | the same TAD in a shorter frame with no title, for the page |

## Rebuild

```bash
S=plugins/chronicle/scripts/chronicle
$S check docs/chronicle-overview/story.json
$S build docs/chronicle-overview/story.json --out /tmp/overview
$S animate build docs/chronicle-overview/tad/animation-page.json --out /tmp/overview-tad --formats svg,png
mkdir -p /tmp/overview/motion
cp /tmp/overview-tad/animation.svg /tmp/overview/motion/chronicle-tad.svg
cp /tmp/overview-tad/poster.png /tmp/overview/motion/chronicle-tad-poster.png
$S animate build docs/chronicle-overview/tad/animation.json --out /tmp/overview-export --formats svg,html,png,gif,mp4
$S animate build docs/chronicle-overview/plugin-diagram/animation.json --out /tmp/plugin-export --formats svg,html,png,gif
```

Publish `/tmp/overview/artifact.html` with the Artifact tool. Its `files` map is
`publish-files.json` plus `motion/chronicle-tad.svg` and `motion/chronicle-tad-poster.png`.

Figures were gathered on 27 Oct 2026 at commit `c7984d8`. Refresh `facts.json` before
reusing the page for a later release.
