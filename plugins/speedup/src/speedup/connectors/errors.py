"""Errors connectors raise; the entry point turns them into one `error:` line."""

from __future__ import annotations


class SourceError(RuntimeError):
    """A request the source refused or answered with an error."""


class AuthError(SourceError):
    """The keys or token were rejected."""


class NetworkError(SourceError):
    """The host could not be reached after retries."""
