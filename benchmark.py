"""Benchmark & ablation harness (Day 9).

Runs the three scenarios from the proposal against one authorized domain and
prints a comparison table so results can go straight into the evaluation report:

  1. baseline   -- active DNS only (wordlist brute-force, no OSINT, no ML)
  2. no-ai      -- passive OSINT + active DNS, but ML predictor disabled
  3. full       -- OSINT + active + ML predictor (the complete design)

Metrics reported: hosts discovered, hosts resolved, high-risk findings, DNS
queries sent (a stealth/efficiency proxy) and wall-clock seconds.

    python benchmark.py example.com
    python benchmark.py example.com --shodan

⚠ Authorized targets only.
"""
from __future__ import annotations

import sys

from rich.console import Console
from rich.table import Table

from core.config import ScanConfig
from core.arb import AdaptiveReconBrain

console = Console()

SCENARIOS = [
    # label,      mode,      brute, use_ml, use_crtsh
    ("baseline",  "active",  True,  False,  False),
    ("no-ai",     "hybrid",  True,  False,  True),
    ("full (AI)", "hybrid",  True,  True,   True),
]


def run_scenario(domain: str, mode: str, brute: bool, use_ml: bool,
                 use_crtsh: bool, use_shodan: bool) -> dict:
    config = ScanConfig(
        domain=domain, mode=mode, brute=brute, use_ml=use_ml,
        use_crtsh=use_crtsh, use_shodan=use_shodan, qps=25, jitter=0.05,
    )
    brain = AdaptiveReconBrain(config, quiet=True)
    result = brain.run()
    risk = result.meta.get("risk", {})
    return {
        "hosts": len(result.hosts),
        "resolved": len(result.resolved_hosts),
        "high_risk": risk.get("high_risk_count", 0),
        "queries": result.meta["stealth_stats"]["queries"],
        "seconds": result.meta["duration_sec"],
    }


def main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("--")]
    if not args:
        console.print("[red]Usage: python benchmark.py <domain> [--shodan][/red]")
        return 1
    domain = args[0]
    use_shodan = "--shodan" in argv

    console.print(f"[bold]Benchmarking[/bold] {domain} — 3 scenarios (authorized only)\n")
    rows = []
    for label, mode, brute, use_ml, use_crtsh in SCENARIOS:
        console.print(f"  running [cyan]{label}[/cyan] …")
        stats = run_scenario(domain, mode, brute, use_ml, use_crtsh, use_shodan)
        rows.append((label, stats))

    table = Table(title=f"Ablation results — {domain}")
    table.add_column("Scenario", style="cyan")
    for col in ("Hosts", "Resolved", "High-risk", "Queries", "Seconds"):
        table.add_column(col, justify="right")
    for label, s in rows:
        table.add_row(label, str(s["hosts"]), str(s["resolved"]),
                      str(s["high_risk"]), str(s["queries"]), str(s["seconds"]))
    console.print(table)

    # Efficiency: new resolved hosts per 100 queries.
    console.print("\n[bold]Efficiency (resolved per 100 queries):[/bold]")
    for label, s in rows:
        eff = (s["resolved"] / s["queries"] * 100) if s["queries"] else 0
        console.print(f"  {label:12} {eff:5.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
