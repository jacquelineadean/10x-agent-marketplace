"""Errors the collectors raise; the entry point turns each into one line for the user."""

from __future__ import annotations


class SourceError(RuntimeError):
    """A system refused a request or answered with something a collector cannot use."""


class AuthError(SourceError):
    """The system rejected the credentials (HTTP 401 or 403)."""


class NetworkError(SourceError):
    """The system could not be reached after retries."""
