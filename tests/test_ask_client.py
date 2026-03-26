import asyncio

from ha_ask.client import AskClient
from ha_ask.config import Config
from ha_ask.dispatch import ask_question
from ha_ask.types import Answer, AskSpec


def _config() -> Config:
    return Config(
        api_url="https://home.example.com",
        token="cfg-token",
        notify_action="notify.mobile_app_phone",
        satellite_entity_id="assist_satellite.kitchen",
        discord_turn_service_url="http://discord-turn.local",
    )


def test_ask_client_ask_question_uses_config_defaults(monkeypatch):
    captured = {}
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    def _fake_dispatch(**kwargs):
        captured.update(kwargs)
        return expected

    monkeypatch.setattr("ha_ask.dispatch.ask_question", _fake_dispatch)

    client = AskClient(_config())
    result = client.ask_question(channel="discord", spec=AskSpec(question="Q"), discord_action="123456")

    assert result == expected
    assert captured["api_url"] == "https://home.example.com/api/"
    assert captured["token"] == "cfg-token"
    assert captured["notify_action"] == "notify.mobile_app_phone"
    assert captured["satellite_entity_id"] == "assist_satellite.kitchen"
    assert captured["discord_turn_service_url"] == "http://discord-turn.local"
    assert captured["discord_action"] == "123456"


def test_ask_client_ask_question_per_call_overrides(monkeypatch):
    captured = {}

    def _fake_dispatch(**kwargs):
        captured.update(kwargs)
        return {"id": None, "sentence": None, "slots": {}, "meta": {}, "error": None}

    monkeypatch.setattr("ha_ask.dispatch.ask_question", _fake_dispatch)

    client = AskClient(_config())
    client.ask_question(
        channel="satellite",
        spec=AskSpec(question="Q"),
        api_url="http://override.local",
        token="override-token",
        notify_action="notify.override",
        satellite_entity_id="assist_satellite.office",
        discord_turn_service_url="http://discord-override.local",
    )

    assert captured["api_url"] == "http://override.local"
    assert captured["token"] == "override-token"
    assert captured["notify_action"] == "notify.override"
    assert captured["satellite_entity_id"] == "assist_satellite.office"
    assert captured["discord_turn_service_url"] == "http://discord-override.local"


def test_ask_client_methods_route_channel_arguments(monkeypatch):
    calls = []

    def _fake_question(**kwargs):
        calls.append(("question", kwargs))
        return {"id": None, "sentence": "q", "slots": {}, "meta": {}, "error": None}

    def _fake_choice(**kwargs):
        calls.append(("choice", kwargs))
        return {"id": "yes", "sentence": "yes", "slots": {}, "meta": {}, "error": None}

    def _fake_freeform(**kwargs):
        calls.append(("freeform", kwargs))
        return {"id": None, "sentence": "reply", "slots": {}, "meta": {}, "error": None}

    monkeypatch.setattr("ha_ask.dispatch.ask_question", _fake_question)
    monkeypatch.setattr("ha_ask.dispatch.ask_choice", _fake_choice)
    monkeypatch.setattr("ha_ask.dispatch.ask_freeform", _fake_freeform)

    client = AskClient(_config())
    client.ask_question(channel="terminal", spec=AskSpec(question="Terminal?"))
    client.ask_question(channel="satellite", spec=AskSpec(question="Satellite?"))
    client.ask_choice(
        channel="mobile",
        question="Pick?",
        choices=[Answer(id="yes", sentences=["yes"], title="Yes")],
    )
    client.ask_freeform(channel="discord", question="Discord?", discord_action="123")

    assert [kind for kind, _ in calls] == ["question", "question", "choice", "freeform"]
    assert calls[0][1]["channel"] == "terminal"
    assert calls[1][1]["channel"] == "satellite"
    assert calls[2][1]["channel"] == "mobile"
    assert calls[3][1]["channel"] == "discord"
    assert calls[3][1]["discord_action"] == "123"


def test_ask_client_async_methods_use_config_defaults(monkeypatch):
    captured = {"question": {}, "choice": {}, "freeform": {}}

    async def _fake_question_async(**kwargs):
        captured["question"].update(kwargs)
        return {"id": None, "sentence": "async-q", "slots": {}, "meta": {}, "error": None}

    async def _fake_choice_async(**kwargs):
        captured["choice"].update(kwargs)
        return {"id": "yes", "sentence": "yes", "slots": {}, "meta": {}, "error": None}

    async def _fake_freeform_async(**kwargs):
        captured["freeform"].update(kwargs)
        return {"id": None, "sentence": "async-f", "slots": {}, "meta": {}, "error": None}

    monkeypatch.setattr("ha_ask.dispatch.ask_question_async", _fake_question_async)
    monkeypatch.setattr("ha_ask.dispatch.ask_choice_async", _fake_choice_async)
    monkeypatch.setattr("ha_ask.dispatch.ask_freeform_async", _fake_freeform_async)

    client = AskClient(_config())

    async def _run() -> None:
        await client.ask_question_async(channel="satellite", spec=AskSpec(question="Q"))
        await client.ask_choice_async(
            channel="mobile",
            question="Pick",
            choices=[Answer(id="yes", sentences=["yes"], title="Yes")],
        )
        await client.ask_freeform_async(channel="discord", question="Tell me", discord_action="123")

    asyncio.run(_run())

    assert captured["question"]["api_url"] == "https://home.example.com/api/"
    assert captured["choice"]["notify_action"] == "notify.mobile_app_phone"
    assert captured["freeform"]["discord_turn_service_url"] == "http://discord-turn.local"


def test_module_level_ask_question_compatibility_path_unchanged(monkeypatch):
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    monkeypatch.setattr("ha_ask.dispatch.terminal_chan.ask_question", lambda spec: expected)
    monkeypatch.setattr("ha_ask.dispatch.persist_ask_session", lambda **kwargs: "session-1")

    result = ask_question(channel="terminal", spec=AskSpec(question="Compat?"))

    assert result == expected
