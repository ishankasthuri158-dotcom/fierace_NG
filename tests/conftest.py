"""Shared test fixtures. All tests run offline -- no live DNS or HTTP."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


class FakeResolver:
    """Deterministic stand-in for StealthResolver (no network)."""

    def __init__(self, table=None, timeout=5.0):
        # table: {(name, rtype): [values]}
        self.table = table or {}
        self.timeout = timeout
        self.stats = {"queries": 0, "errors": 0, "backoffs": 0}

    def resolve(self, name, rtype="A"):
        self.stats["queries"] += 1
        return list(self.table.get((name, rtype), []))

    def aborted(self):
        return False
