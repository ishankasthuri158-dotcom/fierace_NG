import dns.resolver

RECORD_TYPES = ["A", "AAAA", "MX", "NS", "TXT", "CAA", "SRV"]

def lookup_records(domain):
    results = {}
    resolver = dns.resolver.Resolver()
    for rtype in RECORD_TYPES:
        try:
            answers = resolver.resolve(domain, rtype)
            results[rtype] = [r.to_text() for r in answers]
        except dns.resolver.NoAnswer:
            results[rtype] = []
        except dns.resolver.NXDOMAIN:
            return {"error": "NXDOMAIN"}
        except dns.exception.Timeout:
            results[rtype] = ["TIMEOUT"]
    return results
