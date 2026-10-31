"""Detection and the source picker, from fake environments: no system is called."""

from __future__ import annotations

from collections.abc import Mapping

from sources.core import connections, picker
from sources.core.connections import Connection
from sources.core.detect import NOT_SET_UP, detect
from sources.core.systems import SYSTEMS


def _by_id(
    present: frozenset[str] = frozenset(),
    programs: frozenset[str] = frozenset(),
    connectors: tuple[str, ...] = (),
    connections: Mapping[str, Connection] | None = None,
    agent_systems: frozenset[str] = frozenset(),
) -> dict[str, str]:
    found = detect(set(present), set(programs), connectors, connections or {}, set(agent_systems))
    return {s.system.id: s.text for s in found}


def test_nothing_set_up_says_how_to_connect() -> None:
    assert set(_by_id().values()) == {NOT_SET_UP}


def test_connectors_match_by_whole_word() -> None:
    found = _by_id(connectors=("claude_ai_Atlassian", "plugin:engineering:datadog", "pgadmin"))
    assert found["jira"] == "connected through claude_ai_Atlassian"
    assert found["confluence"] == "connected through claude_ai_Atlassian"
    assert found["datadog"] == "connected through plugin:engineering:datadog"
    assert found["postgres"] == NOT_SET_UP  # "pgadmin" is not the word "pg"


def test_keys_need_a_whole_set_and_never_count_as_a_connector() -> None:
    found = _by_id(present=frozenset({"DD_API_KEY", "DD_APPLICATION_KEY", "JIRA_URL"}))
    assert found["datadog"] == (
        "DD_API_KEY and DD_APPLICATION_KEY set; no connector in this session"
    )
    assert found["jira"] == NOT_SET_UP  # two of the three Jira names are missing


def test_programs_connections_and_the_agent_show_together() -> None:
    named = {"warehouse": connections.connection("warehouse", {"system": "postgres", "host": "db"})}
    found = _by_id(frozenset(), frozenset({"psql", "gh"}), (), named, frozenset({"postgres"}))
    assert found["postgres"] == "sources-db agent; connection warehouse; psql found"
    assert found["github"] == "gh found; no connector in this session"


def test_picker_asks_three_multi_select_questions_of_three_systems() -> None:
    questions = picker.questions(detect(set(), set(), ["github"], {}, set()))
    assert [q["header"] for q in questions] == ["Code & work", "Operations", "Data"]
    assert all(q["multiSelect"] and len(q["options"]) == 3 for q in questions)
    assert all(len(q["header"]) <= 12 for q in questions)
    labels = [o["label"] for q in questions for o in q["options"]]
    assert labels == [s.label for s in SYSTEMS]
    assert questions[0]["options"][0]["description"] == "connected through github"
