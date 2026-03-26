from ask import (
    Answer,
    AskClient,
    AskSpec,
    ChoiceSpec,
    Config,
    FreeformSpec,
    ask_choice,
    ask_freeform,
    ask_question,
)
from ask.config import Config as AskConfig
from ha_ask import AskClient as HAAskClient
from ha_ask.config import Config as HAConfig


def test_preferred_ask_surface_exports_stable_api():
    assert AskClient is not None
    assert AskSpec is not None
    assert ChoiceSpec is not None
    assert FreeformSpec is not None
    assert Answer is not None
    assert ask_question is not None
    assert ask_choice is not None
    assert ask_freeform is not None
    assert Config is AskConfig


def test_compatibility_surface_remains_available():
    assert HAAskClient is AskClient
    assert HAConfig is Config


def test_preferred_and_compat_config_modules_are_equivalent():
    ask_cfg = AskConfig(ha_api_url="https://home.example.com", ha_api_token="token")
    compat_cfg = HAConfig(api_url="https://home.example.com", token="token")

    assert ask_cfg.ha_api_url == compat_cfg.ha_api_url
    assert ask_cfg.ha_api_token == compat_cfg.ha_api_token
