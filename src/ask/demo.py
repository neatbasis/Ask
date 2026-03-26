"""Supported demo entrypoint for Ask."""

from ha_ask.demo import load_demo_constants, main, run_demo

__all__ = ["main", "load_demo_constants", "run_demo"]


if __name__ == "__main__":
    raise SystemExit(main())
