"""Data models for Fierce-NG scan results.

The whole pipeline reads and writes these two structures, so every collector,
the DNS engine, the ML predictor and the graph/risk layer speak the same
language and exporters have a single shape to serialise.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


@dataclass
class Host:
    """A single discovered name (subdomain or the apex itself)."""

    name: str                                        # fully-qualified name
    sources: set[str] = field(default_factory=set)   # crtsh, shodan, brute, ml, axfr
    ips: list[str] = field(default_factory=list)
    cname: str | None = None
    records: dict[str, list[str]] = field(default_factory=dict)
    resolved: bool = False
    risk: int = 0                                    # 0-100
    risk_reasons: list[str] = field(default_factory=list)

    def merge(self, other: "Host") -> None:
        """Fold another observation of the same name into this one."""
        self.sources |= other.sources
        for ip in other.ips:
            if ip not in self.ips:
                self.ips.append(ip)
        self.cname = self.cname or other.cname
        self.resolved = self.resolved or other.resolved
        for rtype, values in other.records.items():
            existing = self.records.setdefault(rtype, [])
            for v in values:
                if v not in existing:
                    existing.append(v)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sources"] = sorted(self.sources)
        return d


@dataclass
class ScanResult:
    """The complete output of one scan."""

    domain: str
    mode: str
    apex_records: dict[str, list[str]] = field(default_factory=dict)
    wildcard: bool = False
    hosts: dict[str, Host] = field(default_factory=dict)   # name -> Host
    meta: dict = field(default_factory=dict)               # timings, counts, config
    manifest: dict = field(default_factory=dict)           # signed run manifest

    def add_host(self, host: Host) -> Host:
        """Add or merge a host by name; returns the canonical stored Host."""
        existing = self.hosts.get(host.name)
        if existing:
            existing.merge(host)
            return existing
        self.hosts[host.name] = host
        return host

    def add_name(self, name: str, source: str) -> Host:
        """Convenience: register a bare name from a source."""
        return self.add_host(Host(name=name, sources={source}))

    @property
    def resolved_hosts(self) -> list[Host]:
        return [h for h in self.hosts.values() if h.resolved]

    def to_dict(self) -> dict:
        return {
            "domain": self.domain,
            "mode": self.mode,
            "apex_records": self.apex_records,
            "wildcard": self.wildcard,
            "hosts": [h.to_dict() for h in sorted(self.hosts.values(), key=lambda x: x.name)],
            "meta": self.meta,
            "manifest": self.manifest,
        }
