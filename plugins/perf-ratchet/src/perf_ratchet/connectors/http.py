"""One JSON-over-HTTPS transport for every metrics source: timeouts, retries, read-only rules.

GET is always allowed. POST is allowed only to paths the connector lists as read-only queries
(Datadog's RUM aggregation, for example); anything else is refused before a request is sent.
Never logs a key, a header or a URL with a query string.
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
from typing import Any

from perf_ratchet import __version__
from perf_ratchet.connectors.errors import AuthError, NetworkError, SourceError

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 4

Opener = Callable[..., Any]
Sleeper = Callable[[float], None]


@dataclass
class JsonTransport:
    name: str
    base_url: str
    headers: Mapping[str, str]
    read_only_posts: frozenset[str] = frozenset()
    allow_plain_http: bool = False
    opener: Opener = urllib.request.urlopen
    sleeper: Sleeper = time.sleep
    max_attempts: int = MAX_ATTEMPTS
    calls: int = field(default=0, init=False)

    def get(self, path: str, params: Mapping[str, str]) -> Any:
        query = urllib.parse.urlencode(params)
        return self._send("GET", f"{self._url(path)}?{query}", None)

    def post_query(self, path: str, body: Any) -> Any:
        """POST a read-only query body. Paths not listed in `read_only_posts` are refused."""
        if path not in self.read_only_posts:
            raise SourceError(f"refusing POST {path}: perf-ratchet only reads from {self.name}")
        return self._send("POST", self._url(path), json.dumps(body).encode("utf-8"))

    def _url(self, path: str) -> str:
        url = self.base_url.rstrip("/") + "/" + path.lstrip("/")
        if url.startswith("https://") or (self.allow_plain_http and url.startswith("http://")):
            return url
        raise SourceError(f"refusing non-https URL for {self.name}: {_path(url)}")

    def _send(self, method: str, url: str, payload: bytes | None) -> Any:
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

    def _once(self, method: str, url: str, payload: bytes | None) -> Any:
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"perf-ratchet/{__version__}",
            **self.headers,
        }
        request = urllib.request.Request(  # noqa: S310  scheme checked in _url: https, or http by opt-in
            url, data=payload, method=method, headers=headers
        )
        self.calls += 1
        try:
            with self.opener(request, timeout=TIMEOUT_SECONDS) as raw:
                return _decode(raw.read())
        except urllib.error.HTTPError as error:
            return self._http_error(error, method, url)
        except urllib.error.URLError as error:
            raise _RetryError(
                f"network error: {error.reason}",
                NetworkError(f"cannot reach {self.name}: {error.reason}"),
            ) from None
        except TimeoutError:
            raise _RetryError("timeout", NetworkError(f"timeout talking to {self.name}")) from None

    def _http_error(self, error: urllib.error.HTTPError, method: str, url: str) -> Any:
        status = error.code
        body = _decode(error.read())
        detail = _detail(body)
        if status in (401, 403):
            raise AuthError(
                f"{self.name} refused the credentials (HTTP "
                f"{status}){': ' + detail if detail else ''}"
            )
        if status == 429:
            raise _RetryError(
                "rate limited",
                SourceError(f"{self.name} rate limit reached; try again later"),
                _retry_after(error.headers),
            )
        if status >= 500:
            raise _RetryError(f"HTTP {status}", SourceError(f"{self.name} answered HTTP {status}"))
        raise SourceError(f"{method} {_path(url)} failed with HTTP {status}: {detail}")


class _RetryError(Exception):
    def __init__(self, why: str, error: SourceError, after: float | None = None) -> None:
        super().__init__(why)
        self.why, self.error, self.after = why, error, after


def _decode(raw: bytes) -> Any:
    if not raw:
        return {}
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {"message": raw[:200].decode("utf-8", errors="replace")}


def _detail(body: Any) -> str:
    if not isinstance(body, dict):
        return ""
    errors = body.get("errors")
    if isinstance(errors, list) and errors:
        return "; ".join(str(e.get("detail", e) if isinstance(e, dict) else e) for e in errors)[
            :300
        ]
    return str(body.get("error") or body.get("message") or "")[:300]


def _path(url: str) -> str:
    return url.split("?", 1)[0]


def _retry_after(headers: Any) -> float | None:
    for name in ("Retry-After", "X-RateLimit-Reset"):
        value = headers.get(name) if headers is not None else None
        if value and str(value).isdigit():
            return max(1.0, min(float(value), 300.0))
    return None
