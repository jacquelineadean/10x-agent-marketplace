"""The script-lane collector for each system: request, window, reach and wire in, a Result out."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from sources.connectors import (
    atlassian,
    databricks,
    datadog,
    oracle,
    pagerduty,
    postgres,
    servicenow,
)
from sources.connectors.github import counts
from sources.connectors.wire import Wire
from sources.core.collect import Result
from sources.core.periods import Window
from sources.core.reach import Reach

Reader = Callable[[Mapping[str, Any], Window, Reach, Wire], Result]

READERS: dict[str, Reader] = {
    "github": counts.read,
    "jira": atlassian.jira,
    "confluence": atlassian.confluence,
    "datadog": datadog.read,
    "pagerduty": pagerduty.read,
    "servicenow": servicenow.read,
    "databricks": databricks.read,
    "postgres": postgres.read,
    "oracle": oracle.read,
}
