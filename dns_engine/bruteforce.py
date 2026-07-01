import dns.resolver
import dns.exception
from rich.console import Console
from rich.progress import track

console = Console()

# Small built-in wordlist (we'll expand this later)
DEFAULT_WORDLIST = [
    "www", "mail", "ftp", "admin", "api", "dev", "staging",
    "test", "vpn", "ssh", "smtp", "pop", "imap", "ns1", "ns2",
    "blog", "shop", "portal", "remote", "login", "app", "web",
    "cdn", "static", "media", "docs", "help", "support", "beta"
]

def bruteforce_subdomains(domain: str, wordlist: list = None) -> list:
    """Try common subdomain names and return ones that resolve."""
    if wordlist is None:
        wordlist = DEFAULT_WORDLIST

    found = []
    console.print(f"\n[bold cyan]Brute-forcing subdomains for: {domain}[/bold cyan]")

    for word in track(wordlist, description="Scanning..."):
        subdomain = f"{word}.{domain}"
        try:
            answers = dns.resolver.resolve(subdomain, "A", lifetime=3)
            ips = [str(r) for r in answers]
            found.append({"subdomain": subdomain, "ips": ips})
            console.print(f"  [green]FOUND[/green] {subdomain} → {ips}")
        except Exception:
            pass  # subdomain doesn't exist, move on

    console.print(f"\n[bold]Found {len(found)} subdomains[/bold]")
    return found
