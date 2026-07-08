"""Fierce-NG command-line interface.

    fierce-ng scan example.com --mode auto --brute --ml
    fierce-ng scan example.com --mode passive --out out/
    fierce-ng scan example.com --diff out/example_com.json   # alert on changes
    fierce-ng train corpus.txt models/subs.json              # train ML model

⚠ Only scan domains you own or are explicitly authorized to test.
"""
from __future__ import annotations

import typer
from rich.console import Console
from rich.table import Table

from core.config import ScanConfig
from core.arb import AdaptiveReconBrain
from core.version import __version__
from exporters import export_all, load_previous, diff_scans, novel_names_from_previous

app = typer.Typer(add_completion=False, help="Fierce-NG: AI-assisted DNS reconnaissance.")
console = Console()


@app.command()
def scan(
    domain: str = typer.Argument(..., help="Target domain (authorized only)."),
    mode: str = typer.Option("hybrid", help="passive | active | hybrid | auto"),
    brute: bool = typer.Option(False, "--brute", help="Enable subdomain brute-force."),
    ml: bool = typer.Option(False, "--ml", help="Use ML predictor for candidates."),
    shodan: bool = typer.Option(False, "--shodan", help="Use Shodan (needs SHODAN_API_KEY)."),
    wordlist: str = typer.Option(None, "--wordlist", "-w", help="Custom wordlist file."),
    qps: float = typer.Option(10.0, help="Max queries/sec per resolver."),
    jitter: float = typer.Option(0.15, help="Random +/- delay (seconds)."),
    out: str = typer.Option("out", "--out", "-o", help="Output directory."),
    diff: str = typer.Option(None, "--diff", help="Previous JSON to diff/alert against."),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Suppress progress output."),
):
    """Run a reconnaissance scan and export all artifacts."""
    config = ScanConfig(
        domain=domain, mode=mode, brute=brute, use_ml=ml,
        use_shodan=shodan, wordlist=wordlist, qps=qps, jitter=jitter,
    )

    previous = load_previous(diff) if diff else None

    brain = AdaptiveReconBrain(config, quiet=quiet)
    result = brain.run()

    # Second pass for novelty risk if diffing.
    if previous:
        novel = novel_names_from_previous(previous, result.hosts.keys())
        if novel:
            from graph import RiskAssessor
            RiskAssessor(brain.engine).assess(result, novel_names=novel)

    graph = getattr(brain, "_result_graph", None)
    written = export_all(result, graph=graph, outdir=out)
    result.manifest = result.manifest  # ensure present

    if not quiet:
        _print_summary(result, written)

    if previous:
        report = diff_scans(previous, result.to_dict())
        _print_diff(report)


def _print_summary(result, written: dict) -> None:
    risk = result.meta.get("risk", {})
    table = Table(title=f"\nFierce-NG results — {result.domain}", show_lines=False)
    table.add_column("Host", style="cyan")
    table.add_column("Address", style="white")
    table.add_column("Risk", justify="right")
    table.add_column("Findings", style="yellow")
    ranked = sorted(result.hosts.values(), key=lambda h: (-h.risk, h.name))
    for host in ranked[:25]:
        addr = ", ".join(host.ips) or (host.cname or "—")
        style = "red" if host.risk >= 60 else ("yellow" if host.risk >= 30 else "")
        table.add_row(host.name, addr, f"[{style}]{host.risk}[/{style}]" if style else str(host.risk),
                      " | ".join(host.risk_reasons) or "")
    console.print(table)

    hygiene = risk.get("hygiene", {})
    console.print(f"\n[bold]Email/cert hygiene:[/bold] "
                  f"SPF={'✓' if hygiene.get('spf') else '✗'} "
                  f"DMARC={'✓' if hygiene.get('dmarc') else '✗'} "
                  f"CAA={'✓' if hygiene.get('caa') else '✗'}")
    console.print(f"[bold]Discovered:[/bold] {len(result.hosts)} hosts "
                  f"({result.meta.get('counts',{}).get('resolved',0)} resolved), "
                  f"{risk.get('high_risk_count',0)} high-risk")
    console.print("\n[bold]Artifacts written:[/bold]")
    for key, path in written.items():
        console.print(f"  {key:9} → {path}")


def _print_diff(report: dict) -> None:
    console.print("\n[bold magenta]── Diff vs previous scan ──[/bold magenta]")
    console.print(f"  New: {len(report['new_hosts'])}  "
                  f"Removed: {len(report['removed_hosts'])}  "
                  f"Risk changes: {len(report['risk_changes'])}")
    for alert in report["alerts"]:
        console.print(f"  [red]![/red] {alert}")


@app.command()
def train(
    corpus: str = typer.Argument(None, help="Corpus file (1 host/label per line). Omit for built-in."),
    output: str = typer.Argument("models/subdomains.pkl", help="Model output path."),
    order: int = typer.Option(3, help="N-gram order."),
):
    """Train the ML subdomain predictor."""
    from ml_predictor.train import train_from_file, default_model
    if corpus:
        model = train_from_file(corpus, order=order)
        console.print(f"Trained on {model.trained_on} labels from {corpus}")
    else:
        model = default_model(order=order)
        console.print(f"Trained on {model.trained_on} built-in labels")
    import os
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    model.save(output)
    console.print(f"[green]Saved[/green] → {output}")


@app.command()
def version():
    """Print the Fierce-NG version."""
    console.print(f"fierce-ng {__version__}")


def run() -> None:
    """Console-script entry point (see pyproject.toml)."""
    app()


if __name__ == "__main__":
    app()
