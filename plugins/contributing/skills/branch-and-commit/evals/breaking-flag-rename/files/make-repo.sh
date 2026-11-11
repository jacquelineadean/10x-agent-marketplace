#!/usr/bin/env bash
# Builds a CLI repo on main with an uncommitted change that renames the --out flag to --output.
set -eu
mkdir -p repo && cd repo
git init -q -b main
git config user.email dev@example.com && git config user.name "Dev"
mkdir -p exporter
cat > exporter/cli.py <<'P'
import argparse

def parse(argv):
    p = argparse.ArgumentParser(prog="exporter")
    p.add_argument("--out", required=True, help="output file")
    return p.parse_args(argv)
P
echo "Usage: exporter --out report.csv" > README.md
cat > CONTRIBUTING.md <<'T'
Commits follow Conventional Commits. Scopes: `cli`, `core`, `docs`. We release with semantic-release.
T
git add -A && git commit -qm "feat(cli): initial exporter"
cat > exporter/cli.py <<'P'
import argparse

def parse(argv):
    p = argparse.ArgumentParser(prog="exporter")
    p.add_argument("--output", "-o", required=True, help="output file")
    return p.parse_args(argv)
P
echo "Usage: exporter --output report.csv" > README.md
