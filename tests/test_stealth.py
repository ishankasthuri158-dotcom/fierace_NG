import time

from stealth.orchestrator import StealthResolver


def test_resolver_rotation_cycles():
    sr = StealthResolver(resolvers=["1.1.1.1", "8.8.8.8", "9.9.9.9"], qps=1000, jitter=0)
    picks = [sr._next_resolver() for _ in range(6)]
    assert picks == ["1.1.1.1", "8.8.8.8", "9.9.9.9", "1.1.1.1", "8.8.8.8", "9.9.9.9"]


def test_qps_pacing_enforces_minimum_interval():
    # 20 qps -> >=50ms between queries to the same resolver.
    sr = StealthResolver(resolvers=["1.1.1.1"], qps=20, jitter=0)
    t0 = time.monotonic()
    sr._pace("1.1.1.1")
    sr._pace("1.1.1.1")
    elapsed = time.monotonic() - t0
    assert elapsed >= 0.045  # ~50ms, allow scheduling slack


def test_backoff_triggers_on_error_spike():
    sr = StealthResolver(resolvers=["1.1.1.1"], qps=1000, jitter=0)
    for _ in range(15):
        sr._record(error=True)
    assert sr._backoff > 0
    assert sr.stats["backoffs"] > 0


def test_aborts_only_on_sustained_failure():
    sr = StealthResolver(resolvers=["1.1.1.1"], qps=1000, jitter=0, max_errors=250)
    # A few errors mixed with successes must NOT abort.
    for _ in range(5):
        sr._record(error=True)
        sr._record(error=False)
    assert not sr.aborted()
    # Sustained failure (window fills with errors) should abort.
    for _ in range(60):
        sr._record(error=True)
    assert sr.aborted()
