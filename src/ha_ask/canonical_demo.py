"""Compatibility wrapper for the old demo module path."""

from .demo import load_demo_constants, main, run_demo

run_canonical_demo = run_demo

__all__ = ["main", "load_demo_constants", "run_canonical_demo"]


if __name__ == "__main__":
    raise SystemExit(main())
