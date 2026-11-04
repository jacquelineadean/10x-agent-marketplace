#!/usr/bin/env bash
# Fails when a plugin folder is missing from marketplace.json, release-please-config.json or
# .release-please-manifest.json, or when its version differs between them. release-please
# keeps them in step; this catches a hand edit or a plugin added without its release entries.
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

marketplace=.claude-plugin/marketplace.json
config=release-please-config.json
manifest=.release-please-manifest.json
failures=0

fail() {
  echo "::error::$1"
  failures=$((failures + 1))
}

for plugin_json in plugins/*/.claude-plugin/plugin.json; do
  dir=${plugin_json%/.claude-plugin/plugin.json}
  name=$(jq -r '.name' "$plugin_json")
  plugin_version=$(jq -r '.version // "missing"' "$plugin_json")
  listed_version=$(jq -r --arg n "$name" '.plugins[] | select(.name == $n) | .version // "missing"' "$marketplace")
  manifest_version=$(jq -r --arg d "$dir" '.[$d] // "missing"' "$manifest")
  component=$(jq -r --arg d "$dir" '.packages[$d].component // "missing"' "$config")

  [[ "$name" == "${dir#plugins/}" ]] || fail "$plugin_json: name '$name' differs from folder '${dir#plugins/}'"
  [[ -n "$listed_version" ]] || fail "$marketplace: no entry for '$name'"
  [[ "$component" == "$name" ]] || fail "$config: packages['$dir'].component is '$component', expected '$name'"
  [[ "$listed_version" == "$plugin_version" ]] || fail "$name: marketplace.json has '$listed_version', plugin.json has '$plugin_version'"
  [[ "$manifest_version" == "$plugin_version" ]] || fail "$name: $manifest has '$manifest_version', plugin.json has '$plugin_version'"
  echo "$name $plugin_version"
done

if ((failures > 0)); then
  echo "$failures version check(s) failed. Fix the files above; release-please bumps them together after that."
  exit 1
fi
