"""Passive OSINT collectors: gather subdomains without touching the target."""
from .base import Collector, normalise, in_scope, clean_name, valid_hostname
from .crtsh import CrtShCollector
from .shodan_collector import ShodanCollector


def gather(domain: str, use_crtsh: bool = True, use_shodan: bool = False) -> dict[str, set[str]]:
    """Run enabled collectors; return ``{source_name: {subdomains}}``.

    Only sources that report themselves available actually run, so a missing
    Shodan key silently yields no Shodan results instead of an error.
    """
    results: dict[str, set[str]] = {}
    collectors: list[Collector] = []
    if use_crtsh:
        collectors.append(CrtShCollector())
    if use_shodan:
        collectors.append(ShodanCollector())

    for collector in collectors:
        if collector.available():
            results[collector.name] = collector.collect(domain)
        else:
            results[collector.name] = set()
    return results


__all__ = [
    "Collector",
    "CrtShCollector",
    "ShodanCollector",
    "gather",
    "normalise",
    "in_scope",
    "clean_name",
    "valid_hostname",
]
