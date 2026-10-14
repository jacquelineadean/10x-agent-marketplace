"""Errors the GitHub connector raises; the entry point turns them into messages."""

from __future__ import annotations


class GitHubError(RuntimeError):
    """A request GitHub refused or answered with errors."""


class AuthError(GitHubError):
    """The token was rejected (HTTP 401)."""


class SsoError(GitHubError):
    """An organization requires single sign-on authorization for this token."""

    def __init__(self, organization: str | None, url: str | None) -> None:
        where = f"organization {organization}" if organization else "an organization"
        step = (
            f" Authorize the token at {url}."
            if url
            else (" Authorize the token for SSO on the token settings page (Configure SSO).")
        )
        super().__init__(f"{where} requires SSO authorization for this token.{step}")
        self.organization = organization
        self.url = url


class NetworkError(GitHubError):
    """The host could not be reached after retries."""
