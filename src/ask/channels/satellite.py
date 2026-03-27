# ha_ask/channels/satellite.py
from __future__ import annotations

from typing import Optional, Dict, Any, List

from homeassistant_api import Client

from ..types import AskSpec, AskResult
from ..errors import ERR_NO_MATCH
from ..client import call_service_with_response

DEFAULT_ENTITY = "assist_satellite.esphome_mycroft_assist_satellite"

_TRAILING_PUNCT = " .,!?:;，。！？：；"


def _sanitize_sentence_template(s: str) -> str:
    """
    Normalize templates we send to Assist to maximize match rate.
    (We do NOT normalize the returned 'sentence' beyond .strip().)
    """
    s = s.strip()
    s = s.rstrip(_TRAILING_PUNCT)
    s = " ".join(s.split())
    return s.lower()


def _answers_payload(spec: AskSpec) -> Optional[List[Dict[str, Any]]]:
    """
    Convert Assist-native answers into Assist Satellite payload:

      answers = [{"id": "...", "sentences": ["...","..."]}, ...]

    Returns None if no valid answers exist.
    """
    if not spec.answers:
        return None

    payload: List[Dict[str, Any]] = []
    for a in spec.answers:
        sentences: List[str] = []
        for raw in a.sentences:
            if not isinstance(raw, str):
                continue
            ss = _sanitize_sentence_template(raw)
            if ss:
                sentences.append(ss)

        # de-dupe while preserving order
        deduped = list(dict.fromkeys(sentences))
        if deduped:
            payload.append({"id": a.id, "sentences": deduped})

    return payload or None


def ask_question(client: Client, spec: AskSpec, entity_id: Optional[str] = None) -> AskResult:
    """
    Satellite adapter for assist_satellite.ask_question with semantic normalization:

    - MATCH:        id != None, error == None
    - NO_MATCH:     answers were provided, id == None, sentence != None  => error="no_match"
    - NO_RESPONSE:  transport/service failure classified by client.py     => error="no_response" (sentence None)
    """
    entity_id = entity_id or DEFAULT_ENTITY
    answers = _answers_payload(spec)

    service_kwargs: Dict[str, Any] = dict(
        entity_id=entity_id,
        question=spec.question,
        preannounce=True,
    )
    # Only include answers if present (avoid schema strictness issues).
    if answers is not None:
        service_kwargs["answers"] = answers

    ok, data, err = call_service_with_response(
        client,
        "assist_satellite",
        "ask_question",
        **service_kwargs,
    )

    meta: Dict[str, Any] = {
        "channel": "satellite",
        "entity_id": entity_id,
        "used_answers": bool(answers),
        # keep for debug; drop later if you want
        "answers_payload": answers,
    }

    if not ok:
        return {
            "id": None,
            "sentence": None,
            "slots": {},
            "meta": meta,
            "error": err,
        }

    # Assist returned payload
    sentence = data.get("sentence")
    if isinstance(sentence, str):
        sentence = sentence.strip()
    else:
        sentence = None

    slots = data.get("slots") or {}
    if not isinstance(slots, dict):
        slots = {}

    ans_id = data.get("id")
    if not isinstance(ans_id, str):
        ans_id = None

    # Semantic normalization: distinguish "user spoke but didn't match" from success.
    final_error: Optional[str]
    if err is not None:
        final_error = err
    elif answers is not None and ans_id is None and sentence is not None:
        final_error = ERR_NO_MATCH
    else:
        final_error = None

    return {
        "id": ans_id,
        "sentence": sentence,
        "slots": slots,
        "meta": meta,
        "error": final_error,
    }
