from ha_ask.dispatch import ask_question
from ha_ask.types import AskSpec


def _spec() -> AskSpec:
    return AskSpec(question="Q?")


def test_terminal_channel_routes_without_ha_credentials(monkeypatch):
    expected = {"id": None, "sentence": "hello", "slots": {}, "meta": {"channel": "terminal"}, "error": None}
    persisted: list[dict] = []

    monkeypatch.setattr("ha_ask.dispatch.terminal_chan.ask_question", lambda spec: expected)
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    result = ask_question(channel="terminal", spec=_spec())

    assert result == expected
    assert persisted == [{"channel": "terminal", "spec": _spec(), "result": expected}]


def test_ha_backed_channels_without_credentials_return_deterministic_error(monkeypatch):
    persisted: list[dict] = []
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    for channel, kwargs, expected_error in [
        ("satellite", {}, "missing_ha_credentials"),
        ("mobile", {"notify_action": "notify.phone"}, "missing_ha_credentials"),
        ("discord", {"discord_action": "123"}, "missing_discord_turn_url"),
    ]:
        result = ask_question(channel=channel, spec=_spec(), **kwargs)
        assert result == {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {},
            "error": expected_error,
        }

    assert [entry["channel"] for entry in persisted] == ["satellite", "mobile", "discord"]
    assert [entry["result"]["error"] for entry in persisted] == [
        "missing_ha_credentials",
        "missing_ha_credentials",
        "missing_discord_turn_url",
    ]


def test_missing_notify_and_discord_action_behavior_unchanged(monkeypatch):
    persisted: list[dict] = []
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    mobile = ask_question(channel="mobile", spec=_spec(), api_url="http://ha.local", token="token")
    discord = ask_question(channel="discord", spec=_spec(), api_url="http://discord-turn.local")

    assert mobile["error"] == "missing_notify_action"
    assert discord["error"] == "missing_discord_action"
    assert [entry["channel"] for entry in persisted] == ["mobile", "discord"]


def test_discord_action_falls_back_to_notify_action(monkeypatch):
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    called: dict = {}
    persisted: list[dict] = []

    def _fake_discord(*, spec, service_url, recipient, bearer_token):
        called["recipient"] = recipient
        called["service_url"] = service_url
        called["bearer_token"] = bearer_token
        return expected

    monkeypatch.setattr("ha_ask.dispatch.discord_chan.ask_question", _fake_discord)
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    result = ask_question(
        channel="discord",
        spec=_spec(),
        discord_turn_service_url="http://discord-turn.local",
        token="secret-token",
        notify_action="123456789",
    )

    assert result == expected
    assert called["recipient"] == "123456789"
    assert called["service_url"] == "http://discord-turn.local"
    assert called["bearer_token"] == "secret-token"
    assert len(persisted) == 1
    assert persisted[0]["result"] == expected


def test_discord_requires_dedicated_turn_service_url(monkeypatch):
    monkeypatch.setattr("ha_ask.dispatch.persist_ask_session", lambda **kwargs: "session-1")

    result = ask_question(
        channel="discord",
        spec=_spec(),
        api_url="http://ha.local",
        discord_action="123",
    )

    assert result["error"] == "missing_discord_turn_url"


def test_persist_called_once_for_unknown_channel(monkeypatch):
    persisted: list[dict] = []
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    result = ask_question(channel="bogus", spec=_spec())  # type: ignore[arg-type]

    assert result["error"] == "unknown_channel:bogus"
    assert len(persisted) == 1
    assert persisted[0]["result"] == result
