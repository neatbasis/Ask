"""Compatibility wrapper for the old Ask demo module path."""

from .demo import load_demo_constants, main, run_demo

run_canonical_demo = run_demo

__all__ = ["main", "load_demo_constants", "run_canonical_demo"]
