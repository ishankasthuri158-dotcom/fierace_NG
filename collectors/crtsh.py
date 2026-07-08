"""crt.sh Certificate Transparency collector (Day 3).

Certificate Transparency logs record every TLS certificate issued for a domain.
Because certificates name their subject/SAN hostnames, CT logs are a rich,
*passive* source of real subdomains -- no packets sent to the target at all.

crt.sh exposes a free JSON endpoint (no API key needed):
    https://crt.sh/?q=%25.example.com&output=json
"""
from __future__ import annotations

import time

import requests

from .base import Collector, normalise

CRTSH_URL = "https://crt.sh/"


class CrtShCollector(Collector):
    name = "crtsh"

    def __init__(self, timeout: float = 30.0, retries: int = 3):
        self.timeout = timeout
        self.retries = retries

    def collect(self, domain: str) -> set[str]:
        params = {"q": f"%.{domain}", "output": "json"}
        headers = {"User-Agent": "fierce-ng/0.2 (+research)"}
        rows = None
        # crt.sh frequently returns transient 502/503s; retry with back-off.
        for attempt in range(self.retries):
            try:
                resp = requests.get(
                    CRTSH_URL, params=params, headers=headers, timeout=self.timeout
                )
                resp.raise_for_status()
                rows = resp.json()
                break
            except (requests.RequestException, ValueError):
                if attempt < self.retries - 1:
                    time.sleep(2 * (attempt + 1))
        if rows is None:
            return set()

        raw: list[str] = []
        for row in rows:
            # name_value may hold several newline-separated names.
            raw.extend((row.get("name_value") or "").splitlines())
            cn = row.get("common_name")
            if cn:
                raw.append(cn)
        return normalise(raw, domain)
