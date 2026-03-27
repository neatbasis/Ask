"""Compatibility demo shim.

Canonical demo implementation lives in `ask.demo`.
"""

from ask.demo import load_demo_constants, main, run_demo

__all__ = ["main", "load_demo_constants", "run_demo"]


if __name__ == "__main__":
    raise SystemExit(main())
