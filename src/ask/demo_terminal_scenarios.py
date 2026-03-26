"""Terminal-first Ask demo with a scenario menu.

Run with:
    python -m ask.demo_terminal_scenarios
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from ask import Answer, AskClient, AskSpec
from ask.config import Config


@dataclass(frozen=True)
class Scenario:
    key: str
    label: str
    run: Callable[[AskClient], dict]
    details: str


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
        Scenario("1", "Free-form question", scenario_freeform, "Demonstrates free-form asking."),
        Scenario(
            "2",
            "Multiple-choice classification",
            scenario_classification,
            "Shows stable ids (approve/block) for downstream logic.",
        ),
        Scenario(
            "3",
            "Mission accept / decline / defer",
            scenario_mission_choice,
            "Shows typed and interactive terminal multichoice behavior.",
        ),
        Scenario(
            "4",
            "Required-slot collection",
            scenario_required_slots,
            "Collects deterministic required slots: service + version.",
        ),
        Scenario(
            "5",
            "Template-aware terminal slot demo (best-effort)",
            scenario_template_aware_best_effort,
            "Uses public AskSpec slot collection with template-like sentence patterns.",
        ),
    ]


def print_menu(scenarios: list[Scenario]) -> None:
    print("\nAsk Terminal Scenarios")
    print("======================")
    for scenario in scenarios:
        print(f"{scenario.key}. {scenario.label}")
    print("6. Exit")


def main() -> int:
    client = build_client()
    scenarios = {scenario.key: scenario for scenario in build_scenarios()}

    print("Terminal-first Ask demo")
    print("(All scenarios use channel='terminal' with AskClient + AskSpec.)")

    while True:
        print_menu(list(scenarios.values()))
        choice = input("Select a scenario: ").strip().lower()

        if choice in {"6", "q", "quit", "exit"}:
            print("Goodbye.")
            return 0

        selected = scenarios.get(choice)
        if selected is None:
            print("Invalid selection. Choose 1-6.")
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
