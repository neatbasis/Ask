from __future__ import annotations

from contextlib import contextmanager

from ha_ask.channels import discord
from ha_ask.errors import ERR_TIMEOUT
from ha_ask.types import Answer, AskSpec


class _DummyWS:
    def __init__(self, events):
        self._events = events

    @contextmanager
    def listen_events(self, _event_type: str):
        yield iter(self._events)


def test_discord_choice_maps_answer_slot_bindings_to_slots(monkeypatch):
    monkeypatch.setattr(discord, "call_service_no_response", lambda *args, **kwargs: (True, None))

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

    tag = "discord-choice"
    ws = _DummyWS([
        {"data": {"tag": tag, "action": f"OPT_{tag}_quiet", "reply_text": "please"}},
    ])
    monkeypatch.setattr(discord.uuid, "uuid4", lambda: type("U", (), {"hex": tag})())

    result = discord.ask_question(client=object(), ws=ws, spec=spec, notify_action="notify.discord")

    assert result["id"] == "quiet"
    assert result["slots"] == {"mode": "quiet", "volume": 10}
    assert "slot_evidence" in result["meta"]
    assert result["meta"]["slot_evidence"]["mode"]["source"] == "answer.slot_bindings"
    assert "slot_evidence" not in result["slots"]


def test_discord_reply_mode_done_returns_last_reply(monkeypatch):
    monkeypatch.setattr(discord, "call_service_no_response", lambda *args, **kwargs: (True, None))

    tag = "discord-reply"
    spec = AskSpec(question="Anything else?", answers=None, expect_reply=True, allow_replies=True)
    ws = _DummyWS(
        [
            {"data": {"tag": tag, "action": f"REPLY_{tag}", "reply_text": "first"}},
            {"data": {"tag": tag, "action": f"REPLY_{tag}", "reply_text": "second"}},
            {"data": {"tag": tag, "action": f"DONE_{tag}"}},
        ]
    )
    monkeypatch.setattr(discord.uuid, "uuid4", lambda: type("U", (), {"hex": tag})())

    result = discord.ask_question(client=object(), ws=ws, spec=spec, notify_action="notify.discord")

    assert result["id"] is None
    assert result["sentence"] == "second"
    assert result["slots"] == {}
    assert result["meta"]["mode"] == "reply"


def test_discord_timeout_returns_semantic_timeout(monkeypatch):
    monkeypatch.setattr(discord, "call_service_no_response", lambda *args, **kwargs: (True, None))

    tag = "discord-timeout"
    monkeypatch.setattr(discord.uuid, "uuid4", lambda: type("U", (), {"hex": tag})())

    spec = AskSpec(question="Will timeout", answers=None, expect_reply=True, timeout_s=-1.0)
    ws = _DummyWS([{"data": {"tag": tag, "action": f"REPLY_{tag}", "reply_text": "late"}}])

    result = discord.ask_question(client=object(), ws=ws, spec=spec, notify_action="notify.discord")

    assert result["error"] == ERR_TIMEOUT
    assert result["meta"]["timed_out"] is True
