import dns.resolver
import dns.exception
from rich.console import Console

console = Console()

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CAA", "SRV"]

def query_record(domain: str, record_type: str) -> list:
    """Query a single DNS record type for a domain."""
    try:
        answers = dns.resolver.resolve(domain, record_type, lifetime=5)
        results = []
        for rdata in answers:
            results.append(str(rdata))
        return results
    except dns.resolver.NXDOMAIN:
        return []   # Domain doesn't exist
    except dns.resolver.NoAnswer:
        return []   # Record type doesn't exist for this domain
    except dns.exception.Timeout:
        console.print(f"[yellow]Timeout querying {record_type} for {domain}[/yellow]")
        return []
    except Exception as e:
        return []

def query_all_records(domain: str) -> dict:
    """Query all DNS record types for a domain."""
    console.print(f"\n[bold cyan]Querying DNS records for: {domain}[/bold cyan]")
    results = {}
    for rtype in RECORD_TYPES:
        records = query_record(domain, rtype)
        results[rtype] = records
        if records:
            console.print(f"  [green]{rtype:6}[/green] → {records}")
        else:
            console.print(f"  [dim]{rtype:6} → (none)[/dim]")
    return results

def detect_wildcard(domain: str) -> bool:
    """Check if domain uses wildcard DNS (returns result for any subdomain)."""
    test = f"definitelynotreal-xyz123.{domain}"
    result = query_record(test, "A")
    if result:
        console.print(f"[red]⚠ Wildcard DNS detected on {domain} — results may be unreliable[/red]")
        return True
    return False
