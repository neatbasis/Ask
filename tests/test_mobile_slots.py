from __future__ import annotations

from contextlib import contextmanager

from ha_ask.channels import mobile
from ha_ask.session_store import clear_ask_sessions, get_ask_session, persist_ask_session
from ha_ask.types import Answer, AskSpec


class _DummyWS:
    def __init__(self, events):
        self._events = events

    @contextmanager
    def listen_events(self, _event_type: str):
        yield iter(self._events)


def test_mobile_choice_maps_answer_slot_bindings_to_slots(monkeypatch):
    monkeypatch.setattr(mobile, "call_service_no_response", lambda *args, **kwargs: (True, None))

    spec = AskSpec(
        question="Pick a mode",
        answers=[
            Answer(
                id="quiet",
                title="Quiet",
                sentences=["quiet"],
                slot_bindings={"mode": "quiet", "volume": 10},
            )
        ],
        allow_replies=True,
    )

    tag = "demo-tag"
    ws = _DummyWS(
        [
            {"data": {"tag": tag, "action": f"OPT_{tag}_quiet", "reply_text": "please"}},
        ]
    )
    monkeypatch.setattr(mobile.uuid, "uuid4", lambda: type("U", (), {"hex": tag})())

    result = mobile.ask_question(client=object(), ws=ws, spec=spec, notify_service="mobile_app_phone")

    assert result["id"] == "quiet"
    assert result["slots"] == {"mode": "quiet", "volume": 10}
    assert "slot_evidence" in result["meta"]
    assert result["meta"]["slot_evidence"]["mode"]["source"] == "answer.slot_bindings"
    assert "slot_evidence" not in result["slots"]


def test_persisted_ask_session_contains_prompt_choice_timestamps_replies_and_slot_evidence(monkeypatch):
    clear_ask_sessions()
    monkeypatch.setattr(mobile, "call_service_no_response", lambda *args, **kwargs: (True, None))

    spec = AskSpec(
        question="Select profile",
        answers=[Answer(id="movie", title="Movie", sentences=["movie"], slot_bindings={"profile": "cinema"})],
        allow_replies=True,
    )

    tag = "persist-tag"
    ws = _DummyWS(
        [
            {"data": {"tag": tag, "action": f"OPT_{tag}_movie", "reply_text": "go"}},
        ]
    )
    monkeypatch.setattr(mobile.uuid, "uuid4", lambda: type("U", (), {"hex": tag})())

    result = mobile.ask_question(client=object(), ws=ws, spec=spec, notify_service="mobile_app_phone")
    ask_session_id = persist_ask_session(channel="mobile", spec=spec, result=result)
    record = get_ask_session(ask_session_id)

    assert record is not None
    assert record["prompt"] == "Select profile"
    assert record["chosen_answer_id"] == "movie"
    assert record["replies"] == ["go"]
    assert record["slot_evidence"]["profile"]["source"] == "answer.slot_bindings"
    assert record["t_sent"] is not None
    assert record["t_done"] is not None
