from __future__ import annotations

from tokenwise.connectors.files.store import Transcript, load_session
from tokenwise.core.usage import session_usage, weighted
from tokenwise_helpers import FIXTURES


def test_usage_counted_once_per_message_id_and_tool_results_matched() -> None:
    session = load_session(Transcript(FIXTURES / "session-abc.jsonl", "abc"))

    assert [r.id for r in session.responses] == ["msg_A", "msg_B"]
    first = session.responses[0].usage
    assert (first.cache_write_1h, first.cache_write_5m, first.cache_read) == (1000, 0, 20000)
    bash, edit = session.tools
    assert bash.command == "uv run pytest -q"
    assert bash.is_error and bash.result_chars == len("Exit code 1\n1 failed")
    assert edit.path == "/work/app/parser.py" and not edit.is_error
    assert edit.result_chars == len("The file was updated.")
    assert session.prompts == ["Fix the failing test in parser.py"]
    assert (session.cwd, session.branch) == ("/work/app", "main")


def test_weights_follow_price_multiples() -> None:
    session = load_session(Transcript(FIXTURES / "session-abc.jsonl", "abc"))
    first = session.responses[0]
    # 3 input + 2.0 x 1,000 (1-hour write) + 0.05 x 20,000 (5.5 read) + 5 x 150 output
    assert weighted(first) == 3 + 2000 + 1000 + 750

    usage = session_usage(session)
    assert usage["responses"] == 2
    assert usage["peak_context"] == 21_205
    assert usage["models"] == {"claude-opus-5-5": 2}
    assert usage["efforts"] == {"high": 2}
