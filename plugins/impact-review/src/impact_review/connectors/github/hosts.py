"""API endpoints for github.com, GitHub Enterprise Cloud, Enterprise Server and ghe.com."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Endpoints:
    host: str
    graphql_url: str
    rest_url: str


def normalize_host(host: str) -> str:
    cleaned = host.strip().lower()
    for prefix in ("https://", "http://"):
        cleaned = cleaned.removeprefix(prefix)
    cleaned = cleaned.strip("/")
    if not cleaned or "/" in cleaned or " " in cleaned:
        raise ValueError(f"invalid GitHub host {host!r}")
    return cleaned


def endpoints_for(host: str) -> Endpoints:
    """github.com and Enterprise Cloud share api.github.com; ghe.com gets api.<sub>.ghe.com;
    every other host is an Enterprise Server with /api/graphql and /api/v3."""
    name = normalize_host(host)
    if name in ("github.com", "api.github.com", "www.github.com"):
        return Endpoints("github.com", "https://api.github.com/graphql", "https://api.github.com")
    if name.endswith(".ghe.com"):
        api = name if name.startswith("api.") else f"api.{name}"
        return Endpoints(name.removeprefix("api."), f"https://{api}/graphql", f"https://{api}")
    return Endpoints(name, f"https://{name}/api/graphql", f"https://{name}/api/v3")
