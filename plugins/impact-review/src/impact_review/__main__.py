"""Wiring: build the GitHub connector from settings and hand it to the CLI."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from impact_review.config.settings import load_environment
from impact_review.connectors.github.hosts import endpoints_for
from impact_review.connectors.github.http import GitHubTransport
from impact_review.connectors.github.source import GitHubSource
from impact_review.connectors.github.token import resolve_token
from impact_review.core.ports import ActivitySource
from impact_review.entrypoints.cli.main import run


def main(argv: Sequence[str] | None = None) -> int:
    env = load_environment()

    def make_source(host: str) -> ActivitySource:
        endpoints = endpoints_for(host)
        return GitHubSource(GitHubTransport(endpoints, resolve_token(env, endpoints.host)))

    return run(argv, make_source, env)


if __name__ == "__main__":
    sys.exit(main())
