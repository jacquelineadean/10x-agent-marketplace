"""Wiring: `python -m tokenwise` runs the command line."""

from __future__ import annotations

import sys

from tokenwise.entrypoints.cli.main import run

if __name__ == "__main__":
    sys.exit(run())
