"""Compatibility module alias for :mod:`ask.dispatch`.

`ha_ask` remains a migration import path. This module is intentionally aliased
to the canonical dispatch module so monkeypatch/import seams stay consistent
with current authority ownership in `ask`.
"""

from ask import dispatch as _canonical_dispatch
import sys

sys.modules[__name__] = _canonical_dispatch
