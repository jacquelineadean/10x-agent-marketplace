# Exports and where each one goes

`animate build --formats svg,html,png,gif,mp4,webm` writes into `build/`. The default
is `svg,html,png,gif`. PNG, GIF and video need a local Chromium or Chrome (`--browser
PATH` names one); MP4 also needs `ffmpeg` on PATH, and without it `build` writes WebM.

| File | What it is |
| --- | --- |
| `animation.svg` | The animation: one file, no script, CSS keyframes on one loop. Plays in every current browser, inline or as an image. Shows the whole picture where motion is off. |
| `embed.html` | A `<figure>` to paste into a page: the SVG inline, a pause button (CSS only), the description and sources as a caption, and the steps as a list. |
| `index.html` | A page holding the figure, to open locally or publish as an Artifact. |
| `poster.png` | The still: every part on screen, at the frame size. |
| `steps.png` | The end of each step, two to a row: for checking, or as a storyboard. |
| `animation.gif` | 15 frames a second, 960 pixels wide, one palette that keeps flat colors exact. `--gif-fps` and `--gif-width` change it. |
| `animation.mp4` | H.264 at 30 frames a second (`--fps`), plays in every browser, slide tool and chat app. |
| `animation.webm` | VP9, written by OpenCV when `ffmpeg` is missing or asked for. |

`--theme dark` renders PNG, GIF and video in the theme's dark palette.

## Where to use which

| Destination | File | How |
| --- | --- | --- |
| A web page, CMS or docs site that takes HTML | `embed.html` | Paste the fragment. It scales to the column and pauses on its button. |
| Markdown: GitHub README, docs sites, wikis that take images | `animation.svg` | `![description](animation.svg)`. It plays as an image; fonts fall back to the system's sans and mono. |
| A link to share | `index.html` | Publish with the Artifact tool. |
| Slack, Teams, Discord, Jira, Linear, GitHub comments | `animation.gif` | Upload it; GIFs play inline. The checkout example's 26-second GIF is 0.6 MB; use `mp4` where a tool limits GIF size. |
| Notion, Confluence | `animation.gif` or `animation.mp4` | Upload as an image or a video. |
| Email and newsletters | `animation.gif`, with `poster.png` as the fallback | Most mail apps play neither video nor SVG. |
| Google Slides, PowerPoint, Keynote | `animation.mp4` | Insert the video, set it to play automatically and loop. Use `frame.title: false` when the slide has its own title. |
| Print, PDF, a document | `poster.png` | The still shows every part. |

## Embedding

Inline in a page (fonts load; with `frame.theme: auto` the colors follow the viewer's light or dark setting):

```html
<!-- paste the contents of embed.html -->
```

As an image (no fonts load from an image; the system's fonts stand in):

```html
<img src="animation.svg" alt="the meta.description sentence" width="1280" height="720">
```

In a frame, when a site strips `<style>`:

```html
<iframe src="index.html" title="the title" width="1280" height="760" style="border:0"></iframe>
```

Give a GIF or video the `meta.description` sentence as its alt text or caption.

## Accessibility

- The SVG carries a `<title>` and a `<desc>` with the description, the step captions and
  the sources. `embed.html` adds the steps as a list for readers who cannot watch.
- Moving content longer than 5 seconds needs a way to pause (WCAG 2.2.2): `embed.html`
  has one; for a GIF in a page, link the still or the steps.
- Viewers who ask for reduced motion see the still.
