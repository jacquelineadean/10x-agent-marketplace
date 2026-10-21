"""Datadog sites and their API hosts. Keys are only ever sent to one of these hosts."""

from __future__ import annotations

import re

DEFAULT_SITE = "datadoghq.com"
_SITE = re.compile(r"^(?:[a-z0-9-]+\.)?(?:datadoghq\.com|datadoghq\.eu|ddog-gov\.com)$")


def api_url(site: str) -> str:
    """`datadoghq.com` -> `https://api.datadoghq.com`; `us5.datadoghq.com` -> `https://api.us5...`."""
    host = (site or DEFAULT_SITE).strip().lower()
    host = host.removeprefix("https://").removeprefix("app.").rstrip("/")
    if not _SITE.match(host):
        raise ValueError(
            f"'{site}' is not a Datadog site; use datadoghq.com, us3.datadoghq.com, "
            "us5.datadoghq.com, datadoghq.eu, ap1.datadoghq.com, ap2.datadoghq.com or ddog-gov.com"
        )
    return f"https://api.{host}"
