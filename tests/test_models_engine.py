from core.models import Host, ScanResult
from dns_engine.engine import DNSEngine
from tests.conftest import FakeResolver


def test_host_merge_unions_sources_and_ips():
    a = Host(name="x.example.com", sources={"crtsh"}, ips=["1.1.1.1"])
    b = Host(name="x.example.com", sources={"brute"}, ips=["1.1.1.1", "2.2.2.2"], resolved=True)
    a.merge(b)
    assert a.sources == {"crtsh", "brute"}
    assert a.ips == ["1.1.1.1", "2.2.2.2"]
    assert a.resolved is True


def test_scanresult_add_host_merges_by_name():
    r = ScanResult(domain="example.com", mode="hybrid")
    r.add_name("api.example.com", "crtsh")
    r.add_host(Host(name="api.example.com", sources={"brute"}, ips=["1.2.3.4"], resolved=True))
    assert len(r.hosts) == 1
    host = r.hosts["api.example.com"]
    assert host.sources == {"crtsh", "brute"}
    assert host.resolved


def test_engine_resolve_host_uses_resolver():
    resolver = FakeResolver({
        ("www.example.com", "A"): ["93.184.216.34"],
        ("www.example.com", "CNAME"): [],
    })
    engine = DNSEngine(resolver)
    host = engine.resolve_host("www.example.com")
    assert host.resolved
    assert "93.184.216.34" in host.ips


def test_engine_detect_wildcard():
    # Resolver answers for any name -> wildcard.
    class AlwaysResolver(FakeResolver):
        def resolve(self, name, rtype="A"):
            return ["10.0.0.1"] if rtype == "A" else []
    engine = DNSEngine(AlwaysResolver())
    assert engine.detect_wildcard("example.com") is True


def test_engine_no_wildcard():
    engine = DNSEngine(FakeResolver())
    assert engine.detect_wildcard("example.com") is False
