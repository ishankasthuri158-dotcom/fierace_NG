"""Optional Shodan collector. Requires an API key with query credits."""
from __future__ import annotations

import os

import requests

from .base import Collector, normalise

SHODAN_URL = "https://api.shodan.io/dns/domain/{domain}"
SHODAN_API_KEY = "c6vV69yqA6ZCrNkFdhpze3GoORQtrBAq"  #  API KEY 


class ShodanCollector(Collector):
    name = "shodan"

    def __init__(self, api_key: str | None = None, timeout: float = 30.0):
        self.api_key = (
            api_key
            or SHODAN_API_KEY
            or os.environ.get("SHODAN_API_KEY")
        )
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

        # Convert Shodan's relative subdomain labels to full domain names.
        raw: list[str] = []
        for sub in data.get("subdomains", []):
            raw.append(f"{sub}.{domain}")

        for entry in data.get("data", []):
            sub = entry.get("subdomain")
            name = f"{sub}.{domain}" if sub else domain
            raw.append(name)

        return normalise(raw, domain)
