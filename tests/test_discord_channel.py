from __future__ import annotations

import json

from ha_ask.channels import discord
from ha_ask.errors import ERR_TIMEOUT
from ha_ask.types import Answer, AskSpec


class _DummyHTTPResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self._payload).encode("utf-8")


def test_discord_choice_maps_answer_slot_bindings_to_slots(monkeypatch):
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

    monkeypatch.setattr(
        discord.request,
        "urlopen",
        lambda req, timeout: _DummyHTTPResponse(
            {
                "correlation_id": "c-1",
                "status": "answered",
                "response_text": "1",
                "selected_choice_key": "quiet",
                "user_id": 123,
                "channel_id": 456,
                "error": None,
            }
        ),
    )

    result = discord.ask_question(
        spec=spec,
        service_url="http://discord-turn.local",
        recipient="123:456",
    )

    assert result["id"] == "quiet"
    assert result["slots"] == {"mode": "quiet", "volume": 10}
    assert result["meta"]["slot_evidence"]["mode"]["source"] == "answer.slot_bindings"


def test_discord_freeform_uses_response_text(monkeypatch):
    monkeypatch.setattr(
        discord.request,
        "urlopen",
        lambda req, timeout: _DummyHTTPResponse(
            {
                "correlation_id": "c-2",
                "status": "answered",
                "response_text": "second",
                "selected_choice_key": None,
                "user_id": 123,
                "channel_id": 123,
                "error": None,
            }
        ),
    )

    spec = AskSpec(question="Anything else?", answers=None, expect_reply=True, allow_replies=True)
    result = discord.ask_question(
        spec=spec,
        service_url="http://discord-turn.local",
        recipient="123",
    )

    assert result["id"] is None
    assert result["sentence"] == "second"
    assert result["meta"]["mode"] == "reply"


def test_discord_timeout_returns_semantic_timeout(monkeypatch):
    monkeypatch.setattr(
        discord.request,
        "urlopen",
        lambda req, timeout: _DummyHTTPResponse(
            {
                "correlation_id": "c-3",
                "status": "timed_out",
                "response_text": None,
                "selected_choice_key": None,
                "user_id": 123,
                "channel_id": 123,
                "error": None,
            }
        ),
    )

    spec = AskSpec(question="Will timeout", answers=None, expect_reply=True, timeout_s=1.0)
    result = discord.ask_question(
        spec=spec,
        service_url="http://discord-turn.local",
        recipient="123",
    )

    assert result["error"] == ERR_TIMEOUT
    assert result["meta"]["timed_out"] is True
