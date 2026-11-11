# The architecture block

```json
{"type": "architecture", "svg": "build/tad/animation.svg", "alt": "...", "source": "design",
 "parts": {"orders": {"title": "Order service", "text": "What it does and why it matters."}},
 "pins": [{"part": "payments", "title": "Decision: retry twice", "text": "Why, and what we gave up."}],
 "player": true}
```

| Key | Meaning |
| --- | --- |
| `svg` | an animation built with `animate build ... --formats svg`, beside the story |
| `parts` | details by part id: a TAD node, group or edge id, or a drawn id (`p-web`, `e-orders`, `m3`) |
| `pins` | numbered markers on parts for decisions, risks and open questions |
| `player` | `false` hides the step list and play button |

Clicking a part or a pin shows its details beside the figure; the step list seeks the
animation's clock to each step and pauses there. Readers without scripts get every part and
pin in a list under the figure. `check` refuses a part or pin the SVG does not hold, and a
file that is not a built animation.
