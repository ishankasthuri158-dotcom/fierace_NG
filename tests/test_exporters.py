import json

from core.models import Host, ScanResult
from exporters.formats import to_json, to_csv, to_html
from exporters.manifest import build_manifest, verify_manifest
from exporters.diff import diff_scans, novel_names_from_previous


def _sample():
    r = ScanResult(domain="example.com", mode="hybrid")
    r.add_host(Host(name="example.com", sources={"apex"}, ips=["1.2.3.4"], resolved=True, risk=15))
    r.add_host(Host(name="admin.example.com", sources={"brute"}, ips=["1.2.3.5"],
                    resolved=True, risk=65, risk_reasons=["Sensitive service label exposed: 'admin'"]))
    r.meta = {"counts": {"hosts": 2, "resolved": 2}, "config": {"domain": "example.com"},
              "risk": {"hygiene": {"spf": False, "dmarc": True, "caa": False}, "high_risk_count": 1}}
    return r


def test_json_export_roundtrips():
    data = json.loads(to_json(_sample()))
    assert data["domain"] == "example.com"
    assert len(data["hosts"]) == 2


def test_csv_export_has_header_and_rows():
    csv_text = to_csv(_sample())
    lines = csv_text.strip().splitlines()
    assert lines[0].startswith("name,sources,ips")
    assert len(lines) == 3  # header + 2 hosts


def test_html_export_contains_hosts():
    html = to_html(_sample())
    assert "example.com" in html
    assert "admin.example.com" in html
    assert "Fierce-NG report" in html


def test_manifest_sign_and_verify():
    r = _sample()
    manifest = build_manifest(r, r.meta["config"], signing_key="secret-key")
    assert manifest["signed"] is True
    assert verify_manifest(manifest, signing_key="secret-key") is True
    # Tampering breaks verification.
    manifest["result_sha256"] = "0" * 64
    assert verify_manifest(manifest, signing_key="secret-key") is False


def test_manifest_unsigned_without_key():
    r = _sample()
    manifest = build_manifest(r, r.meta["config"], signing_key=None)
    assert manifest["signed"] is False


def test_diff_detects_new_and_removed():
    prev = {"hosts": [{"name": "example.com", "risk": 10}, {"name": "old.example.com", "risk": 0}]}
    curr = {"hosts": [{"name": "example.com", "risk": 65}, {"name": "new.example.com", "risk": 70}]}
    report = diff_scans(prev, curr)
    assert report["new_hosts"] == ["new.example.com"]
    assert report["removed_hosts"] == ["old.example.com"]
    assert any(c["name"] == "example.com" for c in report["risk_changes"])
    assert any("new.example.com" in a for a in report["alerts"])


def test_novel_names_from_previous():
    prev = {"hosts": [{"name": "a.example.com"}]}
    novel = novel_names_from_previous(prev, ["a.example.com", "b.example.com"])
    assert novel == {"b.example.com"}
