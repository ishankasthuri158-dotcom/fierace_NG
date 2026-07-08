"""Stealth Orchestrator (Day 4).

Wraps dnspython so that every lookup in Fierce-NG is:

* rate-limited per resolver (a simple token-bucket / minimum-interval),
* jittered with a random delay so query timing is not machine-regular,
* spread across a rotating pool of public resolvers, and
* automatically backed-off when the error rate spikes (a sign that a resolver
  is throttling us or that we are being noisy).

The goal is not anonymity but *politeness* -- respecting the ethical, low-noise
posture described in the project proposal.
"""
from __future__ import annotations

import random
import time
from collections import deque

import dns.resolver
import dns.exception


class StealthResolver:
    def __init__(
        self,
        resolvers: list[str] | None = None,
        qps: float = 10.0,
        jitter: float = 0.15,
        timeout: float = 5.0,
        max_errors: int = 250,
        seed: int | None = None,
    ):
        self.resolvers = list(resolvers) if resolvers else ["1.1.1.1", "8.8.8.8"]
        self.qps = max(qps, 0.1)
        self.min_interval = 1.0 / self.qps
        self.jitter = max(jitter, 0.0)
        self.timeout = timeout
        self.max_errors = max_errors
        self._rng = random.Random(seed)

        # Per-resolver last-send timestamp for QPS enforcement.
        self._last_sent: dict[str, float] = {r: 0.0 for r in self.resolvers}
        self._rr = 0  # round-robin cursor

        # Sliding error window for back-off decisions.
        self._recent = deque(maxlen=50)  # True=error, False=ok
        self._backoff = 0.0

        self.stats = {"queries": 0, "errors": 0, "backoffs": 0}

    # -- internals ---------------------------------------------------------
    def _next_resolver(self) -> str:
        r = self.resolvers[self._rr % len(self.resolvers)]
        self._rr += 1
        return r

    def _pace(self, resolver_ip: str) -> None:
        """Respect per-resolver QPS + apply jitter + any active back-off."""
        now = time.monotonic()
        wait = 0.0
        elapsed = now - self._last_sent.get(resolver_ip, 0.0)
        if elapsed < self.min_interval:
            wait += self.min_interval - elapsed
        if self.jitter:
            wait += self._rng.uniform(0, self.jitter)
        wait += self._backoff
        if wait > 0:
            time.sleep(wait)
        self._last_sent[resolver_ip] = time.monotonic()

    def _record(self, error: bool) -> None:
        self._recent.append(error)
        self.stats["queries"] += 1
        if error:
            self.stats["errors"] += 1
        # Back-off if recent error rate is high.
        if len(self._recent) >= 10:
            rate = sum(self._recent) / len(self._recent)
            if rate > 0.4:
                self._backoff = min(self._backoff * 2 + 0.5, 10.0)
                self.stats["backoffs"] += 1
            elif rate < 0.1 and self._backoff:
                self._backoff = max(self._backoff / 2, 0.0)

    # -- public API --------------------------------------------------------
    def resolve(self, name: str, rtype: str = "A") -> list[str]:
        """Resolve ``name``/``rtype`` through a rotated, paced resolver.

        Returns a list of string rdata. Empty list on NXDOMAIN / NoAnswer /
        timeout (callers treat "no data" uniformly).
        """
        resolver_ip = self._next_resolver()
        self._pace(resolver_ip)

        r = dns.resolver.Resolver(configure=False)
        r.nameservers = [resolver_ip]
        r.lifetime = self.timeout
        r.timeout = self.timeout

        try:
            answers = r.resolve(name, rtype)
            self._record(error=False)
            return [rdata.to_text() for rdata in answers]
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            self._record(error=False)   # a clean "no such record" is not an error
            return []
        except (dns.exception.Timeout, dns.exception.DNSException):
            self._record(error=True)
            return []

    def aborted(self) -> bool:
        """True only on sustained failure -- the network is down or we are hard
        blocked. Transient timeouts must not abort a scan; that is what the
        sliding-window back-off is for. We abort if either an absolute ceiling
        is hit, or the recent window is almost entirely errors.
        """
        if self.stats["errors"] >= self.max_errors:
            return True
        if len(self._recent) >= 20 and sum(self._recent) / len(self._recent) > 0.9:
            return True
        return False
