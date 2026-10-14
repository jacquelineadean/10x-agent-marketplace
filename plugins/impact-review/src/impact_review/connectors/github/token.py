"""Token lookup: GITHUB_TOKEN, then GH_TOKEN, then `gh auth token --hostname HOST`."""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable, Mapping

from impact_review.config.settings import TOKEN_NAMES

REQUIRED_SCOPES = ("repo", "read:org", "read:user")

TokenRunner = Callable[[str], str | None]


class MissingTokenError(RuntimeError):
    pass


def gh_cli_token(host: str) -> str | None:
    """Ask the GitHub CLI for the host's token; None when gh is missing or not logged in."""
    gh = shutil.which("gh")
    if gh is None:
        return None
    argv = [gh, "auth", "token", "--hostname", host]
    result = subprocess.run(argv, capture_output=True, text=True, check=False, timeout=15)  # noqa: S603  fixed argv built from a validated host, no shell
    token = result.stdout.strip()
    return token if result.returncode == 0 and token else None


def resolve_token(env: Mapping[str, str], host: str, runner: TokenRunner = gh_cli_token) -> str:
    for name in TOKEN_NAMES:
        value = env.get(name, "").strip()
        if value:
            return value
    token = runner(host)
    if token:
        return token
    names = " or ".join(TOKEN_NAMES)
    raise MissingTokenError(
        f"no GitHub token: set {names}, or run `gh auth login --hostname {host}` "
        f"with scopes {', '.join(REQUIRED_SCOPES)}"
    )
