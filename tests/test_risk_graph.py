from core.models import Host, ScanResult
from dns_engine.engine import DNSEngine
from graph.risk import RiskAssessor
from graph.graph import AttackGraph
from graph.view import graph_to_html, render_html
from tests.conftest import FakeResolver


def _result_with_hosts():
    r = ScanResult(domain="example.com", mode="hybrid")
    r.apex_records = {"A": ["1.2.3.4"]}  # no SPF/CAA in TXT
    r.add_host(Host(name="example.com", sources={"apex"}, ips=["1.2.3.4"], resolved=True))
    r.add_host(Host(name="admin.example.com", sources={"brute"}, ips=["1.2.3.5"], resolved=True))
    r.add_host(Host(name="blog.example.com",
                    sources={"crtsh"}, cname="old-bucket.s3.amazonaws.com", resolved=True))
    return r


def test_apex_hygiene_flags_missing_records():
    engine = DNSEngine(FakeResolver())  # _dmarc returns nothing -> no DMARC
    assessor = RiskAssessor(engine)
    hygiene = assessor.assess_apex(_result_with_hosts())
    assert hygiene["spf"] is False
    assert hygiene["dmarc"] is False
    assert hygiene["caa"] is False
    assert len(hygiene["issues"]) == 3


def test_sensitive_label_raises_risk():
    engine = DNSEngine(FakeResolver())
    r = _result_with_hosts()
    RiskAssessor(engine).assess(r)
    assert r.hosts["admin.example.com"].risk >= 25


def test_dangling_cname_detected():
    # CNAME target does not resolve -> dangling takeover risk.
    engine = DNSEngine(FakeResolver({}))
    r = _result_with_hosts()
    RiskAssessor(engine).assess(r)
    blog = r.hosts["blog.example.com"]
    assert blog.risk >= 70
    assert any("Dangling" in reason for reason in blog.risk_reasons)


def test_dangling_not_flagged_when_target_resolves():
    engine = DNSEngine(FakeResolver({("old-bucket.s3.amazonaws.com", "A"): ["52.1.2.3"]}))
    r = _result_with_hosts()
    RiskAssessor(engine).assess(r)
    blog = r.hosts["blog.example.com"]
    assert not any("Dangling" in reason for reason in blog.risk_reasons)


def test_graph_from_result():
    r = _result_with_hosts()
    g = AttackGraph.from_result(r)
    stats = g.stats()
    assert stats["nodes"] >= 4
    assert stats["edges"] >= 3
    assert "subdomain" in stats["by_type"]
    xml = g.to_graphml()
    assert xml.startswith("<?xml")
    assert "graphml" in xml


def test_graph_html_viewer_embeds_nodes():
    g = AttackGraph.from_result(_result_with_hosts())
    html = graph_to_html(g, "demo")
    assert html.startswith("<!doctype html>")
    assert "admin.example.com" in html
    assert "old-bucket.s3.amazonaws.com" in html


def test_graph_html_viewer_escapes_script_close():
    html = render_html({"nodes": [{"id": "</script><b>x", "type": "subdomain"}], "links": []})
    assert "</script><b>x" not in html
