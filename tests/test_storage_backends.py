from __future__ import annotations

from pathlib import Path
from typing import Any

from ha_ask.schema_flow import run_schema_flow
from ha_ask.session_store import clear_ask_sessions, get_ask_session, persist_ask_session
from ha_ask.storage import (
    InMemoryStorageBackend,
    SQLiteStorageBackend,
    reset_storage_backend,
    set_storage_backend,
)
from ha_ask.types import AskSpec


def test_session_store_remains_compatible_with_in_memory_backend() -> None:
    reset_storage_backend()
    clear_ask_sessions()

    spec = AskSpec(question="Test question", answers=None)
    result: dict[str, Any] = {
        "id": None,
        "sentence": "hello",
        "slots": {},
        "meta": {"replies": ["hello"]},
        "error": None,
    }
    ask_session_id = persist_ask_session(channel="mobile", spec=spec, result=result)
    stored = get_ask_session(ask_session_id)

    assert stored is not None
    assert stored["prompt"] == "Test question"
    assert stored["replies"] == ["hello"]


def test_schema_flow_persists_draft_transitions_and_finalization_to_sqlite(tmp_path: Path) -> None:
    backend = SQLiteStorageBackend(tmp_path / "ha_ask.db")
    set_storage_backend(backend)

    responses: list[dict[str, Any]] = [
        {
            "id": "consent_yes",
            "sentence": "Yes",
            "slots": {"consent_to_contact": True},
            "meta": {"ask_session_id": "session-1", "replies": []},
            "error": None,
        },
        {
            "id": "contact_email",
            "sentence": "Email",
            "slots": {"preferred_contact_method": "email"},
            "meta": {"ask_session_id": "session-2", "replies": []},
            "error": None,
        },
        {
            "id": None,
            "sentence": "America/Los_Angeles",
            "slots": {},
            "meta": {"ask_session_id": "session-3", "replies": ["America/Los_Angeles"]},
            "error": None,
        },
    ]

    def _fake_ask(**_: Any) -> dict[str, Any]:
        return responses.pop(0)

    run_schema_flow(
        schema_name="person_profile_v1",
        partial_input={
            "full_name": "Alex Kim",
            "timezone": None,
            "preferred_contact_method": None,
            "consent_to_contact": None,
        },
        channel="mobile",
        api_url="https://example.local",
        token="token",
        ask_callable=_fake_ask,
        notify_service="mobile_app_phone",
    )

    with backend._connect() as con:  # noqa: SLF001
        draft_row = con.execute(
            "SELECT draft_id, final_object_json, rationale_json FROM schema_drafts"
        ).fetchone()
        evidence_count = con.execute("SELECT COUNT(*) FROM draft_evidence").fetchone()[0]

    assert draft_row is not None
    draft_id = draft_row[0]
    transitions = [state for state, _at in backend.get_draft_transitions(draft_id)]

    assert transitions == ["created", "planned", "asked", "applied", "finalized"]
    assert draft_row[1] is not None
    assert draft_row[2] is not None
    assert evidence_count == 4

    reset_storage_backend()


def test_sqlite_backend_persists_ask_sessions(tmp_path: Path) -> None:
    backend = SQLiteStorageBackend(tmp_path / "ask_sessions.db")
    set_storage_backend(backend)

    spec = AskSpec(question="Durable ask", answers=None)
    result: dict[str, Any] = {
        "id": None,
        "sentence": "done",
        "slots": {},
        "meta": {"replies": ["done"], "slot_evidence": {"x": {"source": "manual"}}},
        "error": None,
    }

    ask_session_id = persist_ask_session(channel="discord", spec=spec, result=result)
    stored = get_ask_session(ask_session_id)

    assert stored is not None
    assert stored["channel"] == "discord"
    assert stored["replies"] == ["done"]
    assert stored["slot_evidence"]["x"]["source"] == "manual"

    reset_storage_backend()


def teardown_module() -> None:
    set_storage_backend(InMemoryStorageBackend())
