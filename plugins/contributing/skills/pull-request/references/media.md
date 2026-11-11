# Screenshots, videos and GIFs for a PR

## Contents

1. What to capture
2. Capture with Playwright
3. Before shots from the base branch
4. Video to GIF or MP4
5. Getting the files into the PR
6. Privacy

## 1. What to capture

| Change | Capture |
| --- | --- |
| Layout, copy, styling | Before and after screenshot of the same view, same viewport |
| Interaction, animation, multi-step flow | Video under 30 seconds, or a GIF under 10 MB |
| Responsive work | One screenshot each at 375, 768 and 1440 px wide |
| Theme work | Light and dark, in a `<picture>` element or a two-column table |
| Error and empty states | One screenshot per state |
| CLI or log output | A `text` code block, no image |

Crop to the part that changed, or use `locator.screenshot()` on the component. A full page
with a 20 px change makes the reviewer hunt for it.

## 2. Capture with Playwright

Use the project's own Playwright if it has one (`npx playwright --version`). Otherwise
`npm i -D playwright` in a scratch folder outside the repo, so the project's lockfile
does not change. Start the app first (`npm run dev` or the project's command).

```js
// capture.mjs: node capture.mjs http://localhost:3000 after
import { chromium } from 'playwright';

const [base = 'http://localhost:3000', label = 'after'] = process.argv.slice(2);
const shots = [
  { name: 'settings', path: '/settings', selector: 'main' },
  { name: 'settings-error', path: '/settings?error=1', selector: 'form' },
];

const browser = await chromium.launch();
const context = await browser.newContext({
  viewport: { width: 1280, height: 800 },
  deviceScaleFactor: 2,          // sharp on high-density screens
  colorScheme: 'light',          // run again with 'dark' for theme work
  recordVideo: { dir: `media/${label}-video`, size: { width: 1280, height: 800 } },
});
const page = await context.newPage();

for (const shot of shots) {
  await page.goto(base + shot.path, { waitUntil: 'networkidle' });
  await page.locator(shot.selector).screenshot({
    path: `media/${label}-${shot.name}.png`,
    animations: 'disabled',
  });
}

// One recorded flow: the video is saved when the context closes.
await page.goto(base + '/settings');
await page.getByLabel('Display name').fill('Ada Lovelace');
await page.getByRole('button', { name: 'Save' }).click();
await page.getByText('Saved').waitFor();

await context.close();
await browser.close();
```

Notes:
- Remove `recordVideo` when you need only screenshots; recording slows the run.
- `animations: 'disabled'` and `waitUntil: 'networkidle'` stop half-drawn frames.
- Freeze dates and random data (seeded fixtures, `page.clock`) so before and after differ
  only by the change.
- Mobile: `newContext({ ...devices['iPhone 13'] })` from `import { devices } from 'playwright'`.
- An existing Playwright test suite can record too: set `use: { video: 'on', screenshot: 'on' }`
  in its config (the test CLI has no flags for these), run `npx playwright test`, then pick
  files from `test-results/`.

## 3. Before shots from the base branch

Run the base branch in a second worktree so the working branch stays untouched. Start its
dev server in the background on a free port, run `capture.mjs` from the scratch folder (it
writes `media/` there), then stop the server and remove the worktree:

```bash
git worktree add ../before origin/main
(cd ../before && npm ci)
(cd ../before && npm run dev -- --port 3001) & server=$!   # flag differs per tool: Vite and Next take --port
# wait until http://localhost:3001 answers, then, in the scratch folder:
node capture.mjs http://localhost:3001 before
kill "$server"
git worktree remove ../before
```

## 4. Video to GIF or MP4

Playwright records `.webm`. GitHub plays an uploaded `.webm`, `.mp4` or `.mov`. A GIF
plays inline anywhere, including from a link to a committed file, and needs no click.

```bash
# MP4, small and widely playable
ffmpeg -i in.webm -c:v libx264 -pix_fmt yuv420p -crf 28 -movflags +faststart out.mp4

# GIF with a generated palette: 10 fps, 800 px wide
ffmpeg -i in.webm -vf "fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" out.gif

# Trim to the part that matters: start at 2 s, keep 8 s
ffmpeg -ss 2 -t 8 -i in.webm ...
```

Over 10 MB, lower `fps` to 8, the width to 640, or trim. Check with `ls -lh`.

## 5. Getting the files into the PR

GitHub has no public API to upload attachments, so pick one route and tell the user which.

**Route A: the user drags them in (default).** Works for every file type, renders videos
as players, and adds nothing to the repo.
1. Save the files where the user can open them, named for their place: `before-settings.png`.
2. In the body, put a placeholder where each goes: `<!-- drag after-settings.png here -->`.
3. Tell the user: "Edit the description and drag in `after-settings.png` under Screenshots
   and `save-flow.mp4` under Recording." List the full paths.

**Route B: commit them and link by SHA.** Use only when the user agrees, because it
writes media into the repo's history.
1. Push the files to a separate branch so the PR branch and `main` stay free of them:
   ```bash
   git switch --orphan pr-media/<branch-slug>   # starts with no tracked files
   cp /path/to/media/after-settings.png /path/to/media/save-flow.gif .   # name each file
   git add after-settings.png save-flow.gif && git commit -m "chore: media for <branch>"
   git push -u origin pr-media/<branch-slug>
   git switch -
   ```
2. Link each file by commit SHA so the link survives later pushes:
   `https://github.com/<owner>/<repo>/blob/<sha>/after-settings.png?raw=true`.
3. Private repos: these links render only for viewers signed in with access. Check the
   Preview tab.
4. Videos linked this way show as a download link, not a player. Convert to GIF, or use
   Route A for the video.
5. Delete the media branch after merge if the repo does not want to keep it.

Never commit screenshots into the PR branch itself unless the repo keeps docs images
there (for example `docs/images/`) and the change updates them.

## 6. Privacy

- Use seed data and test accounts. Real names, emails, customer data, tokens and internal
  URLs in a screenshot are as exposed as in code.
- Uploaded attachments can be reached by anyone with the URL in a public repo, and
  deleting the comment does not always delete the file. Treat an upload as published.
- Crop browser chrome, bookmarks bars and notifications out of the frame.
