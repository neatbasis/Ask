"""Preferred reporting module for Ask."""

from ha_ask.reporting import build_draft_report, main

__all__ = ["main", "build_draft_report"]


if __name__ == "__main__":
    raise SystemExit(main())
