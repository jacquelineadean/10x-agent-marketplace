"""The `sources` command as a host plugin exposes it: `briefing sources ...` runs it here.

A plugin that installs sources registers these two with its own command type, so the
plugin's command line reaches detect, gather, check and digest without repeating them.
The command module is imported when the command runs, so a plugin that never calls it
does not pay for the connectors at startup.
"""

from __future__ import annotations

import argparse
from typing import Any

HELP = "the linked sources command: detect, check, digest"


def add_parser(sub: Any) -> None:
    p = sub.add_parser("sources", help=HELP)
    p.add_argument("args", nargs=argparse.REMAINDER, help="arguments for sources")


def run(args: argparse.Namespace) -> int:
    from sources.entrypoints.cli.main import main

    return main(args.args)
