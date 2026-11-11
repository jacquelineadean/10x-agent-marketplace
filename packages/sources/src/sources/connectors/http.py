"""One JSON-over-HTTPS transport for the collectors: timeouts, retries, read-only rules.

GET is always allowed. POST goes only to the paths a collector names as read-only queries
(Datadog's RUM aggregation, Jira's issue count, Databricks statement execution); any
other POST is refused before a request is sent. Never logs a key, a header or a URL with
its query string.
"""

from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, TypeVar

from sources import __version__
from sources.connectors.errors import AuthError, NetworkError, SourceError

log = logging.getLogger(__name__)
T = TypeVar("T")

TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 4

Opener = Callable[..., Any]
Sleeper = Callable[[float], None]


class RetryError(Exception):
    """A failure worth retrying, carrying the error to raise once the attempts run out."""

    def __init__(self, why: str, error: Exception, after: float | None = None) -> None:
        super().__init__(why)
        self.why, self.error, self.after = why, error, after


def retrying(
    once: Callable[[], T], method: str, url: str, max_attempts: int, sleeper: Sleeper
) -> T:
    """Call `once` until it succeeds, waiting 2, 4, 8 seconds (or what the server asks)."""
    delay = 2.0
    for attempt in range(1, max_attempts + 1):
        try:
            return once()
        except RetryError as retry:
            if attempt == max_attempts:
                raise retry.error from None
            wait = retry.after if retry.after is not None else delay
            log.warning(
                "%s %s: %s; retry %d/%d in %.0fs",
                method,
                path_of(url),
                retry.why,
                attempt,
                max_attempts - 1,
                wait,
            )
            sleeper(wait)
            delay *= 2
    raise NetworkError(f"gave up on {method} {path_of(url)}")


def decode(raw: bytes) -> Any:
    """A JSON body, or the first 200 characters as a message when it is not JSON."""
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"message": raw[:200].decode("utf-8", errors="replace")}


def path_of(url: str) -> str:
    """The URL without its query string, for messages and logs."""
    return url.split("?", 1)[0]


@dataclass
class JsonTransport:
    name: str
    base_url: str
    headers: Mapping[str, str]
    read_only_posts: frozenset[str] = frozenset()
    opener: Opener = urllib.request.urlopen
    sleeper: Sleeper = time.sleep
    max_attempts: int = MAX_ATTEMPTS
    calls: int = field(default=0, init=False)

    def get(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """GET a path under the base URL; list values repeat their key."""
        query = urllib.parse.urlencode(params or {}, doseq=True)
        url = self._url(path) + (f"?{query}" if query else "")
        return retrying(
            lambda: self._once("GET", url, None), "GET", url, self.max_attempts, self.sleeper
        )

    def post_query(self, path: str, body: Any) -> Any:
        """POST a read-only query body. Paths not in `read_only_posts` are refused."""
        if path not in self.read_only_posts:
            raise SourceError(f"refusing POST {path}: sources only reads from {self.name}")
        url, payload = self._url(path), json.dumps(body).encode("utf-8")
        return retrying(
            lambda: self._once("POST", url, payload), "POST", url, self.max_attempts, self.sleeper
        )

    def _url(self, path: str) -> str:
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if not url.startswith("https://"):
            raise SourceError(f"refusing non-https URL for {self.name}: {path_of(url)}")
        return url

    def _once(self, method: str, url: str, payload: bytes | None) -> Any:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"sources/{__version__}",
            **self.headers,
        }
        request = urllib.request.Request(  # noqa: S310  scheme checked in _url: https only
            url, data=payload, method=method, headers=headers
        )
        self.calls += 1
        try:
            with self.opener(request, timeout=TIMEOUT_SECONDS) as raw:
                return decode(raw.read())
        except urllib.error.HTTPError as error:
            return self._http_error(error, method, url)
        except urllib.error.URLError as error:
            raise RetryError(
                f"network error: {error.reason}",
                NetworkError(f"cannot reach {self.name}: {error.reason}"),
            ) from None
        except TimeoutError:
            raise RetryError("timeout", NetworkError(f"timeout talking to {self.name}")) from None

    def _http_error(self, error: urllib.error.HTTPError, method: str, url: str) -> Any:
        status = error.code
        detail = _detail(decode(error.read()))
        if status in (401, 403):
            raise AuthError(
                f"{self.name} refused the credentials (HTTP {status})"
                + (f": {detail}" if detail else "")
            )
        if status == 429:
            raise RetryError(
                "rate limited",
                SourceError(f"{self.name} rate limit reached; try again later"),
                _retry_after(error.headers),
            )
        if status >= 500:
            raise RetryError(f"HTTP {status}", SourceError(f"{self.name} answered HTTP {status}"))
        raise SourceError(f"{method} {path_of(url)} failed with HTTP {status}: {detail}")


def _detail(body: Any) -> str:
    """The error text a system puts in its body, in any of the common shapes."""
    if not isinstance(body, dict):
        return ""
    errors = body.get("errors") or body.get("errorMessages")
    if isinstance(errors, list) and errors:
        text = "; ".join(str(e.get("detail", e) if isinstance(e, dict) else e) for e in errors)
        return text[:300]
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("detail") or "")[:300]
    return str(error or body.get("message") or "")[:300]


def _retry_after(headers: Any) -> float | None:
    for name in ("Retry-After", "X-RateLimit-Reset"):
        value = headers.get(name) if headers is not None else None
        if value and str(value).isdigit():
            return max(1.0, min(float(value), 300.0))
    return None
