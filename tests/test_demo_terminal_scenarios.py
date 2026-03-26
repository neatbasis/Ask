from __future__ import annotations

import importlib


def test_demo_terminal_scenarios_importable() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")

    assert module is not None
    assert callable(module.main)


def test_demo_terminal_scenarios_contains_expected_menu_entries() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")

    scenarios = module.build_scenarios()

    assert [scenario.key for scenario in scenarios] == ["1", "2", "3", "4", "5"]
    assert scenarios[0].label == "Ask an open question"
    assert scenarios[1].label == "Make a stable decision"
    assert scenarios[3].label == "Collect known missing details"
    assert scenarios[4].label == "Try a sentence-style interaction"


def test_scenario_metadata_present_for_main_choices() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")
    scenario_map = {s.key: s for s in module.build_scenarios()}

    for key in ("1", "2", "4", "5"):
        scenario = scenario_map[key]
        assert scenario.recommended_when
        assert scenario.strengths
        assert scenario.limitations


def test_recommendation_mapping() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")

    assert module.recommend_scenario(needs_stable_id=True) == "2"
    assert module.recommend_scenario(needs_deterministic_known_fields=True) == "4"
    assert module.recommend_scenario(prefers_open_text=True) == "1"
    assert module.recommend_scenario(prefers_sentence_style=True) == "5"


def test_explainer_output_is_informative() -> None:
    module = importlib.import_module("ask.demo_terminal_scenarios")
    scenarios = module.build_scenarios()

    output = module.render_scenario_explainer(scenarios)

    assert "Ask an open question" in output
    assert "Make a stable decision" in output
    assert "Collect known missing details" in output
    assert "Try a sentence-style interaction" in output
    assert "Best for:" in output
    assert "Strength:" in output
    assert "Limitation:" in output
