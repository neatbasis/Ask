from __future__ import annotations

from ask.canonical_demo import main as canonical_main
from ask.reporting import build_draft_report
from ha_ask.reporting import main as reporting_main


def test_canonical_demo_module_exposes_callable_main() -> None:
    assert callable(canonical_main)


def test_reporting_module_exposes_report_builder() -> None:
    assert callable(build_draft_report)


def test_reporting_cli_entrypoint_prints_migration_guidance(capsys) -> None:
    exit_code = reporting_main()

    assert exit_code == 2
    captured = capsys.readouterr()
    assert "python -m ask.canonical_demo --output artifacts/demo_report.json" in captured.err
