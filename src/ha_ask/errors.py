# ha_ask/errors.py
from __future__ import annotations
from .types import AskResult

ERR_NO_MATCH = "no_match"
ERR_NO_RESPONSE = "no_response"
ERR_TIMEOUT = "timeout"

def error_kind(err: str | None) -> str | None:
    """
    Returns a stable classifier for downstream logic.
    Unknown error strings remain "other".
    """
    if err is None:
        return None
    if err == ERR_NO_MATCH:
        return ERR_NO_MATCH
    if err == ERR_NO_RESPONSE:
        return ERR_NO_RESPONSE
    if err == ERR_TIMEOUT:
        return ERR_TIMEOUT
    return "other"

def is_ok(res: AskResult) -> bool:
    return res.get("error") is None

def is_match(res: AskResult) -> bool:
    return is_ok(res) and res.get("id") is not None

def is_no_match(res: AskResult) -> bool:
    return res.get("error") == ERR_NO_MATCH

def is_no_response(res: AskResult) -> bool:
    return res.get("error") == ERR_NO_RESPONSE

def is_timeout(res: AskResult) -> bool:
    return res.get("error") == ERR_TIMEOUT

def is_other_error(res: AskResult) -> bool:
    err = res.get("error")
    return err is not None and error_kind(err) == "other"
