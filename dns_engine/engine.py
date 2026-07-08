"""Active DNS engine (Day 2).

Single source of truth for active DNS work in Fierce-NG. Every lookup goes
through a :class:`~stealth.orchestrator.StealthResolver` so record queries,
wildcard detection, AXFR attempts and dangling-CNAME checks all inherit the
same rate-control and jitter.
"""
from __future__ import annotations

import dns.query
import dns.zone
import dns.resolver
import dns.exception

from stealth import StealthResolver
from core.models import Host, ScanResult
from .fingerprints import match_provider

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CAA", "SRV"]

# Random label that should never legitimately exist.
_WILDCARD_PROBE = "wildcard-probe-zzq7x9k2.{domain}"


class DNSEngine:
    def __init__(self, resolver: StealthResolver, record_types: list[str] | None = None):
        self.resolver = resolver
        self.record_types = record_types or RECORD_TYPES

    # -- record queries ----------------------------------------------------
    def query_records(self, name: str, types: list[str] | None = None) -> dict[str, list[str]]:
        """Query several record types for a name; drop empty answers."""
        out: dict[str, list[str]] = {}
        for rtype in (types or self.record_types):
            values = self.resolver.resolve(name, rtype)
            if values:
                out[rtype] = values
        return out

    def resolve_host(self, name: str) -> Host:
        """Resolve one name into a fully-populated :class:`Host`."""
        host = Host(name=name)
        records = self.query_records(name)
        host.records = records
        host.ips = records.get("A", []) + records.get("AAAA", [])
        cnames = self.resolver.resolve(name, "CNAME")
        if cnames:
            host.cname = cnames[0].rstrip(".")
            host.records.setdefault("CNAME", cnames)
        host.resolved = bool(host.ips or host.cname)
        return host

    # -- wildcard detection ------------------------------------------------
    def detect_wildcard(self, domain: str) -> bool:
        """True if the zone answers for a random, non-existent label."""
        probe = _WILDCARD_PROBE.format(domain=domain)
        return bool(self.resolver.resolve(probe, "A") or self.resolver.resolve(probe, "AAAA"))

    # -- zone transfer -----------------------------------------------------
    def try_axfr(self, domain: str) -> list[str]:
        """Attempt AXFR against each authoritative NS. Returns names on success.

        Almost always refused on well-configured zones -- a successful transfer
        is itself a high-value finding (full zone disclosure).
        """
        names: set[str] = set()
        nameservers = self.resolver.resolve(domain, "NS")
        for ns in nameservers:
            ns_host = ns.rstrip(".")
            ns_ips = self.resolver.resolve(ns_host, "A")
            for ns_ip in ns_ips:
                try:
                    xfr = dns.query.xfr(ns_ip, domain, lifetime=self.resolver.timeout)
                    zone = dns.zone.from_xfr(xfr)
                    for rname in zone.nodes.keys():
                        fqdn = str(rname)
                        if fqdn in (".", "@"):
                            names.add(domain)
                        else:
                            names.add(f"{fqdn}.{domain}")
                except Exception:
                    continue  # refused / timeout -> the normal case
        return sorted(names)

    # -- dangling CNAME ----------------------------------------------------
    def check_dangling(self, host: Host) -> str | None:
        """Return a takeover reason string if ``host`` looks dangling."""
        if not host.cname:
            return None
        provider = match_provider(host.cname)
        if not provider:
            return None
        # Strong signal: CNAMEs to a takeover-prone provider but the target
        # itself no longer resolves to an address.
        target_ips = self.resolver.resolve(host.cname, "A")
        if not target_ips:
            return f"Dangling CNAME -> {provider} ({host.cname}); target unresolved"
        return None


def scan_apex(engine: DNSEngine, result: ScanResult, detect_wildcard: bool = True) -> None:
    """Populate apex records + wildcard flag on ``result`` in place."""
    result.apex_records = engine.query_records(result.domain)
    if detect_wildcard:
        result.wildcard = engine.detect_wildcard(result.domain)
