import asyncio

from ha_ask.dispatch import ask_choice_async, ask_freeform_async, ask_question_async
from ha_ask.types import Answer, AskSpec


def test_ask_question_async_delegates_to_sync(monkeypatch):
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    def _fake_ask_question(**kwargs):
        assert kwargs["channel"] == "satellite"
        assert kwargs["ha_api_url"] == "http://preferred.test"
        assert kwargs["ha_api_token"] == "preferred-token"
        assert kwargs["api_url"] == "http://legacy.test"
        assert kwargs["token"] == "legacy-token"
        return expected

    monkeypatch.setattr("ha_ask.dispatch.ask_question", _fake_ask_question)

    result = asyncio.run(
        ask_question_async(
            channel="satellite",
            spec=AskSpec(question="Q"),
            ha_api_url="http://preferred.test",
            ha_api_token="preferred-token",
            api_url="http://legacy.test",
            token="legacy-token",
        )
    )

    assert result == expected


def test_ask_choice_async_delegates_to_sync(monkeypatch):
    expected = {"id": "choice", "sentence": "picked", "slots": {"k": "v"}, "meta": {"m": 1}, "error": None}

    def _fake_ask_choice(**kwargs):
        assert kwargs["channel"] == "mobile"
        assert kwargs["question"] == "Pick one"
        assert kwargs["choices"][0].id == "yes"
        return expected

    monkeypatch.setattr("ha_ask.dispatch.ask_choice", _fake_ask_choice)

    result = asyncio.run(
        ask_choice_async(
            channel="mobile",
            question="Pick one",
            choices=[Answer(id="yes", sentences=["yes"], title="Yes")],
            api_url="http://example.test",
            token="token",
            notify_action="notify.mobile_app_phone",
        )
    )

    assert result is expected


def test_ask_freeform_async_delegates_to_sync(monkeypatch):
    expected = {"id": None, "sentence": "hello world", "slots": {}, "meta": {"channel": "sat"}, "error": None}

    def _fake_ask_freeform(**kwargs):
        assert kwargs["channel"] == "satellite"
        assert kwargs["question"] == "How are you?"
        return expected

    monkeypatch.setattr("ha_ask.dispatch.ask_freeform", _fake_ask_freeform)

    result = asyncio.run(
        ask_freeform_async(
            channel="satellite",
            question="How are you?",
            api_url="http://example.test",
            token="token",
        )
    )

    assert result is expected
