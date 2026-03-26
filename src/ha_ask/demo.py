"""Supported demo entrypoint for Ask."""

from .canonical_demo import load_demo_constants, main, run_canonical_demo as run_demo

__all__ = ["main", "load_demo_constants", "run_demo"]


if __name__ == "__main__":
    raise SystemExit(main())
