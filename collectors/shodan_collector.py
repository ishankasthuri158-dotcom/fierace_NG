"""Shodan collector (Day 3) -- optional, needs a free API key.

Shodan indexes internet-connected hosts. Its DNS endpoint returns subdomains it
has observed for a domain:
    https://api.shodan.io/dns/domain/{domain}?key=API_KEY

The key is read from the ``SHODAN_API_KEY`` environment variable. If it is
absent the collector reports itself unavailable and the pipeline simply skips
it -- Fierce-NG never hard-fails on a missing optional source.
"""
from __future__ import annotations

import os

import requests

from .base import Collector, normalise

SHODAN_URL = "https://api.shodan.io/dns/domain/{domain}"


class ShodanCollector(Collector):
    name = "shodan"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = api_key or os.environ.get("SHODAN_API_KEY")
        self.timeout = timeout

    def available(self) -> bool:
        return bool(self.api_key)

    def collect(self, domain: str) -> set[str]:
        if not self.available():
            return set()
        try:
            resp = requests.get(
                SHODAN_URL.format(domain=domain),
                params={"key": self.api_key},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
        except (requests.RequestException, ValueError):
            return set()

        # Shodan returns bare labels in "subdomains" plus full names in "data".
        raw: list[str] = []
        for sub in data.get("subdomains", []):
            raw.append(f"{sub}.{domain}")
        for entry in data.get("data", []):
            sub = entry.get("subdomain")
            name = f"{sub}.{domain}" if sub else domain
            raw.append(name)
        return normalise(raw, domain)
