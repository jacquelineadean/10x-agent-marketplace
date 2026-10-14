"""One HTTP transport for GraphQL queries and REST GETs: timeouts, retries, backoff.

Never logs the token, the Authorization header or a URL with a query string.
"""

from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field
from email.message import Message
from typing import Any

from impact_review import __version__
from impact_review.connectors.github.errors import AuthError, GitHubError, NetworkError, SsoError
from impact_review.connectors.github.hosts import Endpoints

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 4
_SAML = re.compile(r"saml|single sign-on|sso", re.IGNORECASE)
_SSO_ORG = re.compile(r"organization named ['\"]?([\w.-]+)|organizations?/([\w.-]+)", re.IGNORECASE)

Opener = Callable[..., Any]
Sleeper = Callable[[float], None]


@dataclass
class Response:
    status: int
    headers: Message
    body: Any


@dataclass
class GitHubTransport:
    endpoints: Endpoints
    token: str
    opener: Opener = urllib.request.urlopen
    sleeper: Sleeper = time.sleep
    max_attempts: int = MAX_ATTEMPTS
    calls: int = field(default=0, init=False)

    def graphql(self, query: str, variables: dict[str, Any]) -> tuple[Any, list[str]]:
        """Run a query; return (data, warnings). Mutations are refused before any request."""
        if re.match(r"\s*mutation\b", query):
            raise GitHubError("mutations are not allowed: the collector is read-only")
        payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
        response = self._send("POST", self.endpoints.graphql_url, payload)
        body = response.body if isinstance(response.body, dict) else {}
        errors = [str(err.get("message", err)) for err in body.get("errors") or []]
        data = body.get("data")
        if any(_SAML.search(message) for message in errors):
            raise SsoError(_organization_in(errors), None)
        if data is None:
            raise GitHubError("GraphQL request failed: " + "; ".join(errors or ["no data"]))
        return data, errors

    def rest_get(self, path: str) -> Response:
        """GET a REST path under the API root; 202 comes back as is so callers can retry."""
        return self._send("GET", f"{self.endpoints.rest_url}/{path.lstrip('/')}", None)

    def _send(self, method: str, url: str, payload: bytes | None) -> Response:
        delay = 2.0
        for attempt in range(1, self.max_attempts + 1):
            try:
                return self._once(method, url, payload)
            except _RetryError as retry:
                if attempt == self.max_attempts:
                    raise retry.error from None
                wait = retry.after if retry.after is not None else delay
                log.warning(
                    "%s %s: %s; retry %d/%d in %.0fs",
                    method,
                    _path(url),
                    retry.why,
                    attempt,
                    self.max_attempts - 1,
                    wait,
                )
                self.sleeper(wait)
                delay *= 2
        raise NetworkError(f"gave up on {method} {_path(url)}")

    def _once(self, method: str, url: str, payload: bytes | None) -> Response:
        if not url.startswith("https://"):
            raise GitHubError(f"refusing non-https URL {_path(url)}")
        request = urllib.request.Request(  # noqa: S310  scheme checked above: https only
            url, data=payload, method=method, headers=self._headers()
        )
        self.calls += 1
        try:
            with self.opener(request, timeout=TIMEOUT_SECONDS) as raw:
                return Response(raw.status, raw.headers, _decode(raw.read()))
        except urllib.error.HTTPError as error:
            return self._handle_http_error(error, method, url)
        except urllib.error.URLError as error:
            raise _RetryError(
                f"network error: {error.reason}",
                NetworkError(f"cannot reach {self.endpoints.host}: {error.reason}"),
            ) from None
        except TimeoutError:
            raise _RetryError(
                "timeout", NetworkError(f"timeout talking to {self.endpoints.host}")
            ) from None

    def _handle_http_error(self, error: urllib.error.HTTPError, method: str, url: str) -> Response:
        status, headers = error.code, error.headers
        body = _decode(error.read())
        if status == 401:
            raise AuthError("GitHub rejected the token (HTTP 401); check it has not expired")
        sso = headers.get("X-GitHub-SSO", "")
        if status == 403 and sso.startswith("required"):
            match = re.search(r"url=(\S+)", sso)
            raise SsoError(None, match.group(1) if match else None)
        if status in (403, 429) and _is_rate_limited(headers):
            raise _RetryError(
                "rate limited",
                GitHubError("GitHub rate limit reached; try again later"),
                _retry_after(headers),
            )
        if status >= 500:
            raise _RetryError(f"HTTP {status}", GitHubError(f"GitHub answered HTTP {status}"))
        message = body.get("message", "") if isinstance(body, dict) else ""
        raise GitHubError(f"{method} {_path(url)} failed with HTTP {status}: {message}")

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
            "User-Agent": f"impact-review/{__version__}",
            "X-GitHub-Api-Version": "2022-11-28",
        }


class _RetryError(Exception):
    def __init__(self, why: str, error: GitHubError, after: float | None = None) -> None:
        super().__init__(why)
        self.why, self.error, self.after = why, error, after


def _decode(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"message": raw[:200].decode("utf-8", errors="replace")}


def _path(url: str) -> str:
    return url.split("?", 1)[0]


def _is_rate_limited(headers: Message) -> bool:
    return headers.get("Retry-After") is not None or headers.get("X-RateLimit-Remaining") == "0"


def _retry_after(headers: Message) -> float | None:
    value = headers.get("Retry-After")
    if value and value.isdigit():
        return float(value)
    reset = headers.get("X-RateLimit-Reset")
    if reset and reset.isdigit():
        return max(1.0, min(float(reset) - time.time(), 300.0))
    return None


def _organization_in(messages: list[str]) -> str | None:
    for message in messages:
        if match := _SSO_ORG.search(message):
            return match.group(1) or match.group(2)
    return None
