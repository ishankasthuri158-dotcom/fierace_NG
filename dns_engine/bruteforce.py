"""Subdomain brute-force (Day 2), routed through the stealth orchestrator.

Takes a list of candidate labels (from a wordlist and/or the ML predictor),
resolves each ``label.domain`` under stealth pacing, and returns the ones that
resolve as :class:`Host` objects.
"""
from __future__ import annotations

import os

from rich.console import Console
from rich.progress import track

from stealth import StealthResolver
from core.models import Host
from .engine import DNSEngine

console = Console()

DEFAULT_WORDLIST = [
    "www", "mail", "ftp", "admin", "api", "dev", "staging",
    "test", "vpn", "ssh", "smtp", "pop", "imap", "ns1", "ns2",
    "blog", "shop", "portal", "remote", "login", "app", "web",
    "cdn", "static", "media", "docs", "help", "support", "beta",
    "dashboard", "internal", "git", "jenkins", "grafana", "kibana",
    "mx", "autodiscover", "owa", "vpn2", "gateway", "proxy",
]


def load_wordlist(path: str | None) -> list[str]:
    """Load labels from a file, or fall back to the built-in list."""
    if not path:
        return list(DEFAULT_WORDLIST)
    if not os.path.exists(path):
        console.print(f"[yellow]Wordlist {path} not found; using built-in list[/yellow]")
        return list(DEFAULT_WORDLIST)
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        words = [ln.strip() for ln in fh if ln.strip() and not ln.startswith("#")]
    return words or list(DEFAULT_WORDLIST)


def bruteforce_subdomains(
    domain: str,
    resolver: StealthResolver,
    candidates: list[str] | None = None,
    wordlist_path: str | None = None,
    quiet: bool = False,
) -> list[Host]:
    """Resolve ``label.domain`` for every candidate label; return the hits."""
    labels = candidates if candidates is not None else load_wordlist(wordlist_path)
    # De-dupe while preserving order.
    seen: set[str] = set()
    labels = [x for x in labels if not (x in seen or seen.add(x))]

    engine = DNSEngine(resolver)
    found: list[Host] = []

    use_bar = not quiet and console.is_terminal
    iterator = track(labels, description="Brute-forcing...") if use_bar else labels
    for label in iterator:
        if resolver.aborted():
            if not quiet:
                console.print("[red]Error budget exhausted; stopping brute-force[/red]")
            break
        name = f"{label}.{domain}"
        host = engine.resolve_host(name)
        if host.resolved:
            host.sources.add("brute")
            found.append(host)
            if not quiet:
                target = host.ips or [host.cname]
                console.print(f"  [green]FOUND[/green] {name} -> {target}")

    if not quiet:
        console.print(f"[bold]Brute-force found {len(found)} subdomains[/bold]")
    return found
