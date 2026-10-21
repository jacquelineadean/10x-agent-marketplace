"""Model token estimate for one report. Bytes divided by 4, rounded up, as in impact-review."""

from __future__ import annotations

import math
from typing import Any

DEFAULT_CAP = 25_000
DIGEST_TOKEN_CAP = 3_000
INSTRUCTIONS_DEFAULT = 2_500
SYSTEM_OVERHEAD = 5_000
OUTPUT_ALLOWANCE = 6_000
CONVERSATION_ALLOWANCE = 3_000


def tokens_for(byte_count: int) -> int:
    return math.ceil(byte_count / 4)


def estimate_budget(digest_bytes: int, instructions_bytes: int | None, cap: int) -> dict[str, Any]:
    """Five parts summed against `cap`; the write-up writer is the one model step reading data."""
    parts = {
        "digest": min(tokens_for(digest_bytes), DIGEST_TOKEN_CAP),
        "outline_and_writer_instructions": (
            INSTRUCTIONS_DEFAULT if instructions_bytes is None else tokens_for(instructions_bytes)
        ),
        "system_overhead": SYSTEM_OVERHEAD,
        "output_allowance": OUTPUT_ALLOWANCE,
        "main_conversation": CONVERSATION_ALLOWANCE,
    }
    total = sum(parts.values())
    return {"parts": parts, "estimated_tokens": total, "cap": cap, "within_cap": total <= cap}
