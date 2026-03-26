from __future__ import annotations

import importlib


def test_demo_terminal_scenarios_importable() -> None:
    module = importlib.import_module("demo_terminal_scenarios")

    assert module is not None
    assert callable(module.main)


def test_demo_terminal_scenarios_contains_expected_menu_entries() -> None:
    module = importlib.import_module("demo_terminal_scenarios")

    scenarios = module.build_scenarios()

    assert [scenario.key for scenario in scenarios] == ["1", "2", "3", "4", "5"]
    assert scenarios[0].label == "Free-form question"
    assert "best-effort" in scenarios[4].label.lower()
