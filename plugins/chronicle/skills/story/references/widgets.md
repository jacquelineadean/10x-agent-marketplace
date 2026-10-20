# Widgets: a figure written for one page

Use a widget only when no block fits: a drill where the reader puts steps in order, a
calibration exercise, a simulator with a model the blocks do not have, a game that
teaches one idea. A widget is one script and an optional stylesheet in the run folder.

```json
{"type": "widget", "name": "pack-drill", "title": "Pack the order",
 "subtitle": "Tap the steps in the order the warehouse does them.",
 "script": "widgets/pack-drill.js", "style": "widgets/pack-drill.css",
 "data": {"steps": ["Pick", "Pack", "Label", "Scan", "Ship"]},
 "fallback": "The warehouse picks, packs, labels, scans and ships every order.",
 "source": "jira"}
```

## The script

Write only the body of a function. The build wraps it as
`function (root, data, kit) { ... }` and the page calls it once.

- `root`: an empty element inside the figure, between its heading and its source line.
- `data`: the block's `data`, with fact tokens filled in and `"@path"` references
  replaced by fact values, like every other figure.
- `kit`: the page's own helpers, so the widget looks like the rest of the page.

| `kit.` | Does |
| --- | --- |
| `html(tag, className, text, parent)` | creates an element; text goes in as text |
| `svg(tag, attrs, parent)`, `text(parent, x, y, string, attrs)` | creates SVG elements and labels |
| `fmt(value, kind)` | formats numbers like the charts: `int`, `dec1`, `pct`, `money`, `ms`, `compact` |
| `fmtDate(date, style)`, `parseDate(iso)`, `label(x)` | dates the way the page writes them |
| `color(name)` | a CSS color for `accent`, `legacy`, `s1` to `s6` or a theme color |
| `linear(d0, d1, r0, r1)`, `ticks(lo, hi, n)`, `clamp`, `ease` | scales and easing |
| `tip.show(build, x, y)`, `tip.hide()`, `tip.at(event)` | the page's tooltip |
| `icon(svgParent, name, x, y, scale)` | the progress-bar icons: parcel, van, ball, rocket... |
| `word(key, fallback)` | the theme's word for a control, such as `word("next", "Next")` |
| `chart(mountElement, chartSpec)` | draws any built-in chart into an element |
| `onScroll(fn(viewportHeight))`, `onFrame(fn(viewportHeight, time))` | scroll and animation hooks |
| `store.get(key)`, `store.set(key, value)` | per-reader storage that survives blocked storage |
| `reduceMotion` | true when the reader asked for less motion |

## Rules

`chronicle check` refuses a widget script that uses `innerHTML`, `outerHTML`,
`insertAdjacentHTML`, `document.write`, `eval`, `Function(`, `fetch`, `XMLHttpRequest`,
`WebSocket`, `sendBeacon`, `import(`, `localStorage`, `sessionStorage`, `indexedDB`,
`document.cookie`, `postMessage` or any `http` URL. A widget draws from its data and
nothing else, and puts every string into the page as text.

- Scope the stylesheet under `.w-<name>` (the figure carries that class) and use the
  theme's variables: `var(--accent)`, `var(--ink)`, `var(--surface)`, `var(--f-ui)`,
  `var(--c-<name>)`. The checker refuses `@import` and `url(...)`.
- Make it work by keyboard: buttons, not clickable divs; visible focus.
- Respect `kit.reduceMotion`.
- Keep it to one idea and under 200 lines. If it grows, it is two figures.
- Write `fallback` text: it shows where scripts do not run and in the page's static HTML.
- Check it in the browser at desktop and phone width before publishing.

## Example

```js
// Tap the steps in order; a wrong tap shakes, a right one moves to the done list.
var steps = data.steps || [];
var order = steps.slice().sort(function () { return Math.random() - 0.5; });
var next = 0;
var done = kit.html("ol", "done", null, root);
var pool = kit.html("div", "pool", null, root);
var msg = kit.html("p", "msg", "Tap the first step.", root);
order.forEach(function (name) {
  var b = kit.html("button", "chip", name, pool);
  b.type = "button";
  b.addEventListener("click", function () {
    if (name !== steps[next]) { msg.textContent = "Not yet: what comes before " + name + "?"; return; }
    kit.html("li", null, name, done);
    b.remove();
    next += 1;
    msg.textContent = next === steps.length ? "That is the order every parcel takes." : "Next step?";
  });
});
```
