from __future__ import annotations

import importlib
from pathlib import Path


def test_preferred_import_surface_contract() -> None:
    import ask
    from ask import Answer, AskClient, AskSpec
    from ask.config import Config

    assert ask is not None
    assert AskClient is not None
    assert AskSpec is not None
    assert Answer is not None
    assert Config is not None


def test_compatibility_import_surface_contract() -> None:
    import ha_ask
    from ha_ask import Answer, AskClient, AskSpec

    assert ha_ask is not None
    assert AskClient is not None
    assert AskSpec is not None
    assert Answer is not None


def test_demo_terminal_module_importable_via_preferred_package() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")

    assert module is not None
    assert callable(module.main)


def test_preferred_package_no_longer_reexports_public_surface_from_ha_ask() -> None:
    init_source = Path("src/ask/__init__.py").read_text(encoding="utf-8")

    assert "from ha_ask import" not in init_source
