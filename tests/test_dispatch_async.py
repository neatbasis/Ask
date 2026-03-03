import asyncio

from ha_ask.dispatch import ask_question_async
from ha_ask.types import AskSpec


def test_ask_question_async_delegates_to_sync(monkeypatch):
    expected = {"id": "ok", "sentence": "ok", "slots": {}, "meta": {}, "error": None}

    def _fake_ask_question(**kwargs):
        assert kwargs["channel"] == "satellite"
        return expected

    monkeypatch.setattr("ha_ask.dispatch.ask_question", _fake_ask_question)

    result = asyncio.run(
        ask_question_async(
            channel="satellite",
            spec=AskSpec(question="Q"),
            api_url="http://example.test",
            token="token",
        )
    )

    assert result == expected
