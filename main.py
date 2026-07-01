import typer
from rich.console import Console
from dns_engine.resolver import query_all_records, detect_wildcard
from dns_engine.bruteforce import bruteforce_subdomains

app = typer.Typer()
console = Console()

@app.command()
def scan(
    domain: str = typer.Argument(..., help="Target domain to scan"),
    mode: str = typer.Option("passive", help="Mode: passive / active / hybrid"),
    brute: bool = typer.Option(False, "--brute", help="Enable subdomain brute-force")
):
    """Fierce-NG: AI-Assisted DNS Reconnaissance Framework"""
    console.print(f"\n[bold green]Fierce-NG[/bold green] v0.1")
    console.print(f"Target : [cyan]{domain}[/cyan]")
    console.print(f"Mode   : [yellow]{mode}[/yellow]")

    # Step 1: Check for wildcard DNS
    detect_wildcard(domain)

    # Step 2: Query all DNS records
    records = query_all_records(domain)

    # Step 3: Brute-force subdomains if requested
    if brute:
        subdomains = bruteforce_subdomains(domain)

if __name__ == "__main__":
    app()
