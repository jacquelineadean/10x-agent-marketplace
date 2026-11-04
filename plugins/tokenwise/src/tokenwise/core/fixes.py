"""Apply and undo low-tier fixes on a Claude Code settings object. Pure: no file access.

Each change records the value it replaced, so `undo` restores the file exactly.
"""

from __future__ import annotations

import copy
from typing import Any

from tokenwise.core.model import Finding


def applicable(findings: list[Finding]) -> list[Finding]:
    return [f for f in findings if f.tier == "low" and f.fix is not None]


def apply_fixes(
    settings: dict[str, Any], findings: list[Finding]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return new settings and the changes made; fixes already in place are skipped."""
    result = copy.deepcopy(settings)
    changes: list[dict[str, Any]] = []
    for finding in applicable(findings):
        fix = finding.fix or {}
        if fix["kind"] == "deny":
            deny = result.setdefault("permissions", {}).setdefault("deny", [])
            if fix["rule"] in deny:
                continue
            deny.append(fix["rule"])
            changes.append({"finding": finding.id, "kind": "deny", "rule": fix["rule"]})
        elif fix["kind"] == "env":
            env = result.setdefault("env", {})
            if env.get(fix["name"]) == fix["value"]:
                continue
            changes.append(
                {
                    "finding": finding.id,
                    "kind": "env",
                    "name": fix["name"],
                    "value": fix["value"],
                    "previous": env.get(fix["name"]),
                }
            )
            env[fix["name"]] = fix["value"]
        else:
            raise ValueError(f"unknown fix kind '{fix['kind']}' in {finding.id}")
    return result, changes


def undo_changes(settings: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]:
    result = copy.deepcopy(settings)
    for change in reversed(changes):
        if change["kind"] == "deny":
            deny = result.get("permissions", {}).get("deny", [])
            if change["rule"] in deny:
                deny.remove(change["rule"])
        elif change["kind"] == "env":
            env = result.setdefault("env", {})
            if change.get("previous") is None:
                env.pop(change["name"], None)
            else:
                env[change["name"]] = change["previous"]
    return result


def applied_ids(ledger: list[dict[str, Any]]) -> set[str]:
    """Finding ids applied and not undone; an undone fix is never applied again by the hook."""
    return {change["finding"] for batch in ledger for change in batch.get("changes", [])}
