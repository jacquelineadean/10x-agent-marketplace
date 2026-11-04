from __future__ import annotations

from tokenwise.core.fixes import applied_ids, apply_fixes, undo_changes
from tokenwise.core.guard import record
from tokenwise.core.model import Finding


def _finding(key: str, fix: dict[str, str] | None, tier: str = "low") -> Finding:
    return Finding("rule", key, tier, "t", "e", "a", 10, fix=fix)


DENY = _finding("lock", {"kind": "deny", "rule": "Read(./uv.lock)"})
ENV = _finding("bash", {"kind": "env", "name": "BASH_MAX_OUTPUT_LENGTH", "value": "15000"})


def test_apply_then_undo_restores_settings() -> None:
    before = {"env": {"BASH_MAX_OUTPUT_LENGTH": "40000"}, "permissions": {"allow": ["Bash(ls)"]}}
    after, changes = apply_fixes(before, [DENY, ENV, _finding("x", None)])

    assert after["permissions"]["deny"] == ["Read(./uv.lock)"]
    assert after["env"]["BASH_MAX_OUTPUT_LENGTH"] == "15000"
    assert [c["finding"] for c in changes] == ["rule:lock", "rule:bash"]
    assert before["env"]["BASH_MAX_OUTPUT_LENGTH"] == "40000"
    restored = undo_changes(after, changes)
    assert restored == {**before, "permissions": {"allow": ["Bash(ls)"], "deny": []}}


def test_undo_removes_env_that_was_unset() -> None:
    after, changes = apply_fixes({}, [ENV])
    assert undo_changes(after, changes)["env"] == {}


def test_fix_in_place_and_medium_tier_are_skipped() -> None:
    settings = {"permissions": {"deny": ["Read(./uv.lock)"]}}
    medium = _finding("m", {"kind": "deny", "rule": "Read(./a)"}, tier="medium")
    _, changes = apply_fixes(settings, [DENY, medium])
    assert changes == []


def test_ledger_ids_include_undone_batches() -> None:
    ledger = [
        {"changes": [{"finding": "a"}], "undone": "2026-11-01"},
        {"changes": [{"finding": "b"}]},
    ]
    assert applied_ids(ledger) == {"a", "b"}


def test_guard_warns_once_at_third_failure_and_resets_on_success() -> None:
    state: dict[str, object] = {}
    messages = []
    for _ in range(4):
        state, message = record(state, "make  test", failed=True)
        messages.append(message)
    assert [bool(m) for m in messages] == [False, False, True, False]

    state, _ = record(state, "make test", failed=False)
    state, first = record(state, "make test", failed=True)
    assert state["failures"] == {"make test": 1} and first == ""
