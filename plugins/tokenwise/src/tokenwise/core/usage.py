"""Token totals per session, priced in input-token equivalents.

Anthropic list prices (platform.claude.com pricing page, November 2026) put every model's
categories at fixed multiples of its base input price: 5-minute cache write 1.25x, 1-hour
cache write 2x, output 5x. Cache reads cost 0.05x on the 5.5 models and 0.1x on older ones.
Weighting by these multiples ranks waste the same way dollars would, without a price table.
"""

from __future__ import annotations

from collections import Counter
from typing import Any

from tokenwise.core.model import Response, Session

WRITE_5M, WRITE_1H, OUTPUT = 1.25, 2.0, 5.0
CACHE_READ_DEFAULT = 0.1
CACHE_READ_BY_MODEL = {"-5-5": 0.05}


def cache_read_weight(model: str) -> float:
    return next((w for tag, w in CACHE_READ_BY_MODEL.items() if tag in model), CACHE_READ_DEFAULT)


def weighted(response: Response) -> float:
    u = response.usage
    return (
        u.input_tokens
        + WRITE_5M * u.cache_write_5m
        + WRITE_1H * u.cache_write_1h
        + cache_read_weight(response.model) * u.cache_read
        + OUTPUT * u.output_tokens
    )


def session_usage(session: Session) -> dict[str, Any]:
    responses = session.responses
    read = sum(r.usage.cache_read for r in responses)
    context = sum(r.usage.context for r in responses)
    output_weight = sum(OUTPUT * r.usage.output_tokens for r in responses)
    total = sum(weighted(r) for r in responses)
    return {
        "session": session.id,
        "agent_type": session.agent_type,
        "started": session.started,
        "responses": len(responses),
        "tool_calls": len(session.tools),
        "input_tokens": sum(r.usage.input_tokens for r in responses),
        "cache_write_tokens": sum(
            r.usage.cache_write_5m + r.usage.cache_write_1h for r in responses
        ),
        "cache_read_tokens": read,
        "output_tokens": sum(r.usage.output_tokens for r in responses),
        "weighted_tokens": round(total),
        "output_share": round(output_weight / total, 3) if total else 0.0,
        "cache_hit": round(read / context, 3) if context else 0.0,
        "peak_context": max((r.usage.context for r in responses), default=0),
        "models": dict(Counter(r.model for r in responses if r.model)),
        "efforts": dict(Counter(r.effort for r in responses if r.effort)),
    }
