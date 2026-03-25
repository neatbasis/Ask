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

    for channel, kwargs in [
        ("satellite", {}),
        ("mobile", {"notify_action": "notify.phone"}),
        ("discord", {"discord_action": "notify.discord"}),
    ]:
        result = ask_question(channel=channel, spec=_spec(), **kwargs)
        assert result == {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": {},
            "error": "missing_ha_credentials",
        }

    assert [entry["channel"] for entry in persisted] == ["satellite", "mobile", "discord"]
    assert [entry["result"]["error"] for entry in persisted] == [
        "missing_ha_credentials",
        "missing_ha_credentials",
        "missing_ha_credentials",
    ]


def test_missing_notify_and_discord_action_behavior_unchanged(monkeypatch):
    persisted: list[dict] = []
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    mobile = ask_question(channel="mobile", spec=_spec(), api_url="http://ha.local", token="token")
    discord = ask_question(channel="discord", spec=_spec(), api_url="http://ha.local", token="token")

    assert mobile["error"] == "missing_notify_action"
    assert discord["error"] == "missing_discord_action"
    assert [entry["channel"] for entry in persisted] == ["mobile", "discord"]


def test_discord_action_falls_back_to_notify_action(monkeypatch):
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    class _DummyClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return object()

        def __exit__(self, exc_type, exc, tb):
            return False

    called: dict = {}
    persisted: list[dict] = []

    def _fake_discord(client, ws, spec, notify_action):
        called["notify_action"] = notify_action
        return expected

    monkeypatch.setattr("ha_ask.dispatch.Client", _DummyClient)
    monkeypatch.setattr("ha_ask.dispatch.WebsocketClient", _DummyClient)
    monkeypatch.setattr("ha_ask.dispatch.discord_chan.ask_question", _fake_discord)
    monkeypatch.setattr(
        "ha_ask.dispatch.persist_ask_session",
        lambda **kwargs: persisted.append(kwargs) or "session-1",
    )

    result = ask_question(
        channel="discord",
        spec=_spec(),
        api_url="http://ha.local",
        token="token",
        notify_action="notify.mobile_app_phone",
    )

    assert result == expected
    assert called["notify_action"] == "notify.mobile_app_phone"
    assert len(persisted) == 1
    assert persisted[0]["result"] == expected


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
