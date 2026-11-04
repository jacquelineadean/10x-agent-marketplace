"""`metrics.json` and the digest Claude reads. Digest hard cap 12,000 bytes."""

from __future__ import annotations

from typing import Any

from tokenwise.core.model import TIERS, Finding

SCHEMA_VERSION = 1
DIGEST_CAP_BYTES = 12_000
TOP_SESSIONS = 8
_TRIMMED = "\n_Digest trimmed to the 12 KB cap; findings.json holds every finding._\n"


def build_metrics(
    project: str,
    generated_at: str,
    usages: list[dict[str, Any]],
    findings: list[Finding],
    applied: list[dict[str, Any]],
) -> dict[str, Any]:
    main = [u for u in usages if not u["agent_type"]]
    return {
        "schema_version": SCHEMA_VERSION,
        "project": project,
        "generated_at": generated_at,
        "sessions": len(main),
        "subagent_runs": len(usages) - len(main),
        "weighted_tokens": sum(u["weighted_tokens"] for u in usages),
        "output_tokens": sum(u["output_tokens"] for u in usages),
        "cache_read_tokens": sum(u["cache_read_tokens"] for u in usages),
        "at_stake_tokens": sum(f.at_stake for f in findings),
        "by_tier": {t: sum(1 for f in findings if f.tier == t) for t in TIERS},
        "top_sessions": sorted(usages, key=lambda u: -u["weighted_tokens"])[:TOP_SESSIONS],
        "applied": applied,
    }


def render_digest(metrics: dict[str, Any], findings: list[Finding]) -> str:
    for limit in (40, 24, 12, 6, 0):
        text = "\n".join(_lines(metrics, findings[:limit])) + "\n"
        if len(text.encode("utf-8")) <= DIGEST_CAP_BYTES:
            return text
    cut = text.encode("utf-8")[: DIGEST_CAP_BYTES - len(_TRIMMED.encode("utf-8"))]
    return cut.decode("utf-8", errors="ignore") + _TRIMMED


def _lines(metrics: dict[str, Any], findings: list[Finding]) -> list[str]:
    lines = [
        f"# Token audit: {metrics['project']}",
        "",
        f"Generated {metrics['generated_at']}. {metrics['sessions']} sessions, "
        f"{metrics['subagent_runs']} subagent runs, {metrics['weighted_tokens']:,} weighted "
        f"tokens (input-token equivalents). Findings put {metrics['at_stake_tokens']:,} at stake.",
        "",
        "## Sessions by cost",
        "| Session | Started | Responses | Weighted | Peak context | Cache hit | Output share |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for u in metrics["top_sessions"]:
        name = u["session"][:8] + (f" ({u['agent_type']})" if u["agent_type"] else "")
        lines.append(
            f"| {name} | {u['started'][:16]} | {u['responses']} | {u['weighted_tokens']:,} | "
            f"{u['peak_context']:,} | {u['cache_hit']:.0%} | {u['output_share']:.0%} |"
        )
    for tier in TIERS:
        tiered = [f for f in findings if f.tier == tier]
        if not tiered:
            continue
        lines += ["", f"## {tier.capitalize()} risk ({len(tiered)})"]
        for f in tiered:
            fix = " Auto-fix available." if f.fix else ""
            lines.append(
                f"- `{f.id[:70]}` {f.title}. {f.evidence}. About {f.at_stake:,} tokens. "
                f"{f.advice}{fix}"
            )
    if metrics["applied"]:
        lines += ["", "## Applied by tokenwise"]
        lines += [
            f"- {c['kind']} {c.get('rule') or c.get('name')} ({c['finding'][:60]})"
            for c in metrics["applied"]
        ]
    return lines
