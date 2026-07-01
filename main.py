import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def scan(
    domain: str = typer.Argument(..., help="Target domain to scan"),
    mode: str = typer.Option("passive", help="Mode: passive / active / hybrid")
):
    """Fierce-NG: AI-Assisted DNS Reconnaissance Framework"""
    console.print(f"\n[bold green]Fierce-NG[/bold green] v0.1")
    console.print(f"Target : [cyan]{domain}[/cyan]")
    console.print(f"Mode   : [yellow]{mode}[/yellow]\n")

if __name__ == "__main__":
    app()
