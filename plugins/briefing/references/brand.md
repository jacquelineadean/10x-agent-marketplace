# Brand kits

A brand kit gives every deck, dashboard and page an organization builds the same colors
and type. `--brand` picks it on `new`, `check` and `build`:

| Value | File |
| --- | --- |
| `run` (default) | `brand.json` in the run folder, when there is one |
| `repo` | `.brand/brand.json` at the git root |
| `config` | `$XDG_CONFIG_HOME/chronicle/brand.json`, else `~/.config/chronicle/brand.json` |
| a path | that file |

`new --brand repo|config|PATH` copies the kit into the run folder, so each run keeps the
kit it was built with.

```json
{
  "schema_version": 1,
  "name": "Fernhill Outfitters",
  "palette": {"paper": "#FBF8F1", "ink": "#1F2A24", "accent": "#2F6B4F", "legacy": "#B5532D",
              "series": ["#2F6B4F", "#B5532D", "#3E6E9E"]},
  "dark": {"accent": "#7FC2A0"},
  "fonts": {"display": "Fraunces", "body": "Source Serif 4", "ui": "DM Sans"}
}
```

The kit fills the story's `theme` where the theme is silent. A theme value that differs
from the kit wins, and `check` warns that the page departs from the kit. Fonts must be in
the font list; contrast rules still apply, so an ink that fails on its paper stops the build.
