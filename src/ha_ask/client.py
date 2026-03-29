"""Compatibility module alias for :mod:`ask.client`.

`ha_ask` is a migration import path; the canonical implementation authority is
`ask`. Re-exporting only selected symbols caused drift for compatibility callers
that import module-level helpers (`call_service_no_response`, patch seams in
tests, etc). To keep this seam truthful, the legacy module path resolves to the
canonical module object.
"""

from ask import client as _canonical_client
import sys

sys.modules[__name__] = _canonical_client
