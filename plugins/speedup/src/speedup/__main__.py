"""Wiring: build metrics sources from settings and hand them to the CLI."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from speedup.config.settings import (
    datadog_keys,
    load_environment,
    prometheus_token,
    settings_from,
)
from speedup.connectors.datadog.sites import api_url
from speedup.connectors.datadog.source import DatadogSource, datadog_transport
from speedup.connectors.files.store import DataFolder
from speedup.connectors.prometheus.source import PrometheusSource, prometheus_transport
from speedup.core.model import Project
from speedup.core.ports import SeriesSource
from speedup.entrypoints.cli.main import run


def main(argv: Sequence[str] | None = None) -> int:
    env = load_environment()
    settings = settings_from(env)

    def make_source(kind: str, project: Project, data: DataFolder) -> SeriesSource:
        if kind.startswith("datadog"):
            keys = datadog_keys(env)
            site = settings.datadog_site or project.datadog_site
            transport = datadog_transport(api_url(site), keys.api_key, keys.app_key)
            return DatadogSource(transport, data.record_raw)
        if kind == "prometheus":
            url = settings.prometheus_url or project.prometheus_url
            if not url:
                raise ValueError("Prometheus needs PROMETHEUS_URL or sources.prometheus.url")
            return PrometheusSource(
                prometheus_transport(url, prometheus_token(env)), data.record_raw
            )
        raise ValueError(f"no connector for source kind '{kind}'")

    return run(argv, make_source, env)


if __name__ == "__main__":
    sys.exit(main())
