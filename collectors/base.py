"""Shared helpers for passive OSINT collectors."""
from __future__ import annotations

import re


_LABEL = r"[a-zA-Z0-9_](?:[a-zA-Z0-9_-]{0,61}[a-zA-Z0-9_])?"


def clean_name(name: str) -> str:

    """Lower-case, strip wildcards/whitespace/trailing dot from a hostname."""
    name = name.strip().lower().rstrip(".")
    if name.startswith("*."):
        name = name[2:]
    return name


def in_scope(name: str, domain: str) -> bool:
  
    """True if ``name`` is the apex domain or a subdomain of it."""
    domain = domain.lower().rstrip(".")
    return name == domain or name.endswith("." + domain)


def valid_hostname(name: str) -> bool:
    if not name or len(name) > 253:
        return False
    return all(re.fullmatch(_LABEL, label) for label in name.split("."))


def normalise(names, domain: str) -> set[str]:
    
    """Clean, scope-filter and de-duplicate a stream of raw names."""
    out: set[str] = set()
    for raw in names:
        for piece in re.split(r"[\s,]+", raw or ""):
            name = clean_name(piece)
            if name and valid_hostname(name) and in_scope(name, domain):
                out.add(name)
    return out


class Collector:
    """Base passive collector. Subclasses implement :meth:`collect`."""

    name = "base"

    def available(self) -> bool:
        return True

    def collect(self, domain: str) -> set[str]:
        raise NotImplementedError
