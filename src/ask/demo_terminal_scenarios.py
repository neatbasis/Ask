"""Terminal-first Ask demo with a scenario menu.

Run with:
    python -m ask.demo_terminal_scenarios
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ask import Answer, AskClient, AskSpec
from ask.config import Config

EXPLAINER_MENU_KEY = "6"
EXIT_MENU_KEYS = {"7", "q", "quit", "exit"}


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    run: Callable[[AskClient], dict]
    details: str
    recommended_when: str
    strengths: tuple[str, ...]
    limitations: tuple[str, ...]
    supports_open_text: bool
    supports_stable_id: bool
    supports_deterministic_slot_collection: bool
    supports_sentence_style: bool
    requires_known_fields: bool
    supports_machine_actionability: bool


def build_client() -> AskClient:
    """Build a client using explicit config values.

    These Home Assistant fields are placeholders for demo clarity. Terminal channel
    scenarios in this script run locally and do not require Home Assistant transport.
    """

    cfg = Config(
        ha_api_url="https://home.example.com",
        ha_api_token="DEMO_LONG_LIVED_TOKEN",
    )
    return AskClient(cfg)


def print_result(result: dict) -> None:
    print("\nResult")
    print("------")
    print(f"id: {result.get('id')}")
    print(f"sentence: {result.get('sentence')}")
    print(f"slots: {result.get('slots')}")
    print(f"error: {result.get('error')}")
    meta = result.get("meta") or {}
    print(f"meta.channel: {meta.get('channel')}")


def scenario_freeform(client: AskClient) -> dict:
    spec = AskSpec(question="What should we do next?")
    return client.ask_question(channel="terminal", spec=spec)


def scenario_classification(client: AskClient) -> dict:
    spec = AskSpec(
        question="Classify this launch request.",
        answers=[
            Answer(id="approve", title="Approve", sentences=["approve", "allow", "ship it"]),
            Answer(id="block", title="Block", sentences=["block", "deny", "stop"]),
        ],
    )
    return client.ask_question(channel="terminal", spec=spec)


def scenario_mission_choice(client: AskClient) -> dict:
    spec = AskSpec(
        question="Mission command: what should we do?",
        answers=[
            Answer(id="accept_mission", title="Accept Mission", sentences=["accept", "go", "proceed"]),
            Answer(id="decline_mission", title="Decline Mission", sentences=["decline", "abort", "cancel"]),
            Answer(id="defer_mission", title="Defer Mission", sentences=["defer", "later", "not now"]),
        ],
    )
    return client.ask_question(channel="terminal", spec=spec)


def scenario_required_slots(client: AskClient) -> dict:
    spec = AskSpec(
        question="Gather release details.",
        expected_slots=["service", "version"],
    )
    return client.ask_question(channel="terminal", spec=spec)


def scenario_template_aware_best_effort(client: AskClient) -> dict:
    """Best available public-API terminal slot demo.

    AskSpec currently exposes required slots and answer sentence patterns, but does
    not directly expose richer template objects on the public construction surface.
    This scenario truthfully demonstrates the terminal slot-collection fallback path
    available through AskClient + AskSpec today.
    """

    spec = AskSpec(
        question="What should I play?",
        expected_slots=["album", "artist"],
        answers=[
            Answer(
                id="play_album",
                title="Play album",
                sentences=["play {album} by {artist}", "spin {album} from {artist}"],
            )
        ],
    )
    return client.ask_question(channel="terminal", spec=spec)


def build_scenarios() -> list[Scenario]:
    return [
        Scenario(
            key="1",
            label="Ask an open question",
            run=scenario_freeform,
            details="Demonstrates unconstrained free-form asking.",
            recommended_when="You want unconstrained text and do not need a stable downstream id.",
            strengths=("Flexible, natural user input",),
            limitations=("No guaranteed stable decision id for machine branching",),
            supports_open_text=True,
            supports_stable_id=False,
            supports_deterministic_slot_collection=False,
            supports_sentence_style=False,
            requires_known_fields=False,
            supports_machine_actionability=False,
        ),
        Scenario(
            key="2",
            label="Make a stable decision",
            run=scenario_classification,
            details="Returns stable decision ids (approve/block) for downstream logic.",
            recommended_when="A downstream system needs a predictable key (id) from user intent.",
            strengths=("Stable ids are machine-actionable", "Simple bounded choice set"),
            limitations=("Less flexible than open text",),
            supports_open_text=False,
            supports_stable_id=True,
            supports_deterministic_slot_collection=False,
            supports_sentence_style=False,
            requires_known_fields=False,
            supports_machine_actionability=True,
        ),
        Scenario(
            key="3",
            label="Mission-style decision options (extended)",
            run=scenario_mission_choice,
            details="Shows typed and interactive terminal multichoice behavior with three outcomes.",
            recommended_when="You want a richer decision set than binary classification.",
            strengths=("Shows multi-option mission framing",),
            limitations=("Still a bounded chooser, not open exploration",),
            supports_open_text=False,
            supports_stable_id=True,
            supports_deterministic_slot_collection=False,
            supports_sentence_style=False,
            requires_known_fields=False,
            supports_machine_actionability=True,
        ),
        Scenario(
            key="4",
            label="Collect known missing details",
            run=scenario_required_slots,
            details="Collects deterministic required slots: service + version.",
            recommended_when="Required fields are known in advance and deterministic completion matters.",
            strengths=("Deterministic required-slot completion",),
            limitations=("Requires known fields up front",),
            supports_open_text=False,
            supports_stable_id=False,
            supports_deterministic_slot_collection=True,
            supports_sentence_style=False,
            requires_known_fields=True,
            supports_machine_actionability=True,
        ),
        Scenario(
            key="5",
            label="Try a sentence-style interaction",
            run=scenario_template_aware_best_effort,
            details="Uses public AskSpec slot collection with template-like sentence patterns.",
            recommended_when="You think in phrase patterns and want a template-like terminal interaction.",
            strengths=("Phrase-oriented interaction feel",),
            limitations=(
                "Current terminal public API may still fall back to summary-style rendering",
            ),
            supports_open_text=False,
            supports_stable_id=True,
            supports_deterministic_slot_collection=True,
            supports_sentence_style=True,
            requires_known_fields=True,
            supports_machine_actionability=True,
        ),
    ]


def recommend_scenario(
    *,
    needs_stable_id: bool = False,
    needs_deterministic_known_fields: bool = False,
    prefers_open_text: bool = False,
    prefers_sentence_style: bool = False,
) -> str:
    """Return the recommended scenario key for a simple need profile."""

    if needs_stable_id:
        return "2"
    if needs_deterministic_known_fields:
        return "4"
    if prefers_sentence_style:
        return "5"
    if prefers_open_text:
        return "1"
    return "1"


def render_scenario_explainer(scenarios: list[Scenario]) -> str:
    lines: list[str] = []
    lines.append("\nScenario quick guide")
    lines.append("====================")
    lines.append("Use these standards to choose intentionally:")
    lines.append("- best for")
    lines.append("- key strength")
    lines.append("- key limitation")
    lines.append("")

    for scenario in scenarios:
        if scenario.key == "3":
            continue
        lines.append(f"{scenario.key}. {scenario.label}")
        lines.append(f"   Best for: {scenario.recommended_when}")
        lines.append(f"   Strength: {scenario.strengths[0]}")
        lines.append(f"   Limitation: {scenario.limitations[0]}")

    lines.append("")
    lines.append("Quick recommendations:")
    lines.append("- Need a stable downstream key? -> Make a stable decision (2)")
    lines.append("- Need deterministic known-field collection? -> Collect known missing details (4)")
    lines.append("- Need unconstrained text? -> Ask an open question (1)")
    lines.append("- Think in sentence patterns? -> Try a sentence-style interaction (5)")
    lines.append("")
    lines.append("If unsure, start with: 1. Ask an open question.")
    lines.append("Note: Sentence-style terminal behavior is best-effort on today's public API.")
    return "\n".join(lines)


def print_menu(scenarios: list[Scenario]) -> None:
    print("\nAsk Terminal Scenarios")
    print("======================")
    for scenario in scenarios:
        print(f"{scenario.key}. {scenario.label}")
    print(f"{EXPLAINER_MENU_KEY}. I want to know more")
    print("7. Exit")


def main() -> int:
    client = build_client()
    scenarios = {scenario.key: scenario for scenario in build_scenarios()}

    print("Terminal-first Ask demo")
    print("(All scenarios use channel='terminal' with AskClient + AskSpec.)")

    while True:
        print_menu(list(scenarios.values()))
        choice = input("Select a scenario: ").strip().lower()

        if choice in EXIT_MENU_KEYS:
            print("Goodbye.")
            return 0
        if choice == EXPLAINER_MENU_KEY:
            print(render_scenario_explainer(list(scenarios.values())))
            input("\nPress Enter to return to the menu...")
            continue

        selected = scenarios.get(choice)
        if selected is None:
            print("Invalid selection. Choose 1-7.")
            continue

        print(f"\nRunning: {selected.label}")
        print(f"Note: {selected.details}")

        if selected.key == "5":
            print(
                "Note: Full template object rendering is internal today; "
                "this uses the best truthful public AskSpec path."
            )

        result = selected.run(client)
        print_result(result)

        input("\nPress Enter to return to the menu...")


if __name__ == "__main__":
    raise SystemExit(main())
