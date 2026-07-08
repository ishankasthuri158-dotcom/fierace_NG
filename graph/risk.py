"""Risk scoring (Day 6).

Turns raw findings into prioritised, actionable risk. Two levels:

* **Domain (apex) hygiene** -- email/cert posture: SPF, DMARC and CAA. Missing
  records make spoofing or mis-issuance easier, so their absence is a finding.
* **Per-host risk (0-100)** -- dangling CNAMEs (takeover), successful zone
  transfer, exposure of sensitive services, wildcard ambiguity and CT novelty.

Scores are additive then clamped to 0-100 so results can be sorted "worst
first" for the analyst.
"""
from __future__ import annotations

from dns_engine.engine import DNSEngine

# Per-signal risk weights (points added, then clamped to 100).
W_DANGLING = 70          # subdomain takeover -- very risky
W_AXFR = 90              # full zone transfer -- critical disclosure
W_SENSITIVE = 25         # exposed admin/db/ci surface
W_NO_SPF = 15
W_NO_DMARC = 15
W_WEAK_DMARC = 8         # p=none
W_NO_CAA = 8
W_WILDCARD = 5
W_CT_NOVEL = 20          # newly seen in Certificate Transparency

# Labels that suggest a sensitive service is publicly exposed.
SENSITIVE_LABELS = {
    "admin", "administrator", "adm", "phpmyadmin", "pma", "cpanel", "whm",
    "jenkins", "gitlab", "grafana", "kibana", "prometheus", "sonar",
    "db", "database", "mysql", "postgres", "mongo", "redis", "elastic",
    "vpn", "internal", "intranet", "staging", "dev", "test", "uat", "qa",
    "backup", "vault", "secret", "jira", "confluence", "ldap",
}


class RiskAssessor:
    def __init__(self, engine: DNSEngine):
        self.engine = engine

    # -- apex email / cert hygiene ----------------------------------------
    def assess_apex(self, result) -> dict:
        txt = " ".join(result.apex_records.get("TXT", [])).lower()
        has_spf = "v=spf1" in txt
        has_caa = bool(result.apex_records.get("CAA"))

        dmarc_txt = " ".join(self.engine.resolver.resolve(f"_dmarc.{result.domain}", "TXT")).lower()
        has_dmarc = "v=dmarc1" in dmarc_txt
        weak_dmarc = has_dmarc and "p=none" in dmarc_txt

        hygiene = {
            "spf": has_spf,
            "dmarc": has_dmarc,
            "dmarc_policy_weak": weak_dmarc,
            "caa": has_caa,
            "issues": [],
        }
        if not has_spf:
            hygiene["issues"].append("No SPF record (email spoofing easier)")
        if not has_dmarc:
            hygiene["issues"].append("No DMARC record (no anti-spoofing policy)")
        elif weak_dmarc:
            hygiene["issues"].append("DMARC policy is p=none (monitor-only, not enforced)")
        if not has_caa:
            hygiene["issues"].append("No CAA record (any CA may issue certs)")
        return hygiene

    # -- per-host ----------------------------------------------------------
    def assess_host(self, host, result, hygiene: dict, novel_names: set[str]) -> None:
        risk = 0
        reasons: list[str] = []

        if result.meta.get("axfr_names"):
            # Any host learned via a successful AXFR inherits the disclosure.
            if "axfr" in host.sources:
                risk += W_AXFR
                reasons.append("Discovered via successful AXFR (zone transfer allowed)")

        dangling = self.engine.check_dangling(host) if host.cname else None
        if dangling:
            risk += W_DANGLING
            reasons.append(dangling)

        label = host.name.split(".")[0]
        if label in SENSITIVE_LABELS:
            risk += W_SENSITIVE
            reasons.append(f"Sensitive service label exposed: '{label}'")

        if host.name in novel_names:
            risk += W_CT_NOVEL
            reasons.append("New since last scan (CT/OSINT novelty)")

        # Apex host carries the domain-hygiene issues.
        if host.name == result.domain:
            if not hygiene["spf"]:
                risk += W_NO_SPF
                reasons.append("No SPF record")
            if not hygiene["dmarc"]:
                risk += W_NO_DMARC
                reasons.append("No DMARC record")
            elif hygiene["dmarc_policy_weak"]:
                risk += W_WEAK_DMARC
                reasons.append("DMARC p=none (not enforced)")
            if not hygiene["caa"]:
                risk += W_NO_CAA
                reasons.append("No CAA record")
            if result.wildcard:
                risk += W_WILDCARD
                reasons.append("Wildcard DNS (subdomain results ambiguous)")

        host.risk = min(risk, 100)
        host.risk_reasons = reasons

    # -- driver ------------------------------------------------------------
    def assess(self, result, novel_names: set[str] | None = None) -> dict:
        novel_names = novel_names or set()
        hygiene = self.assess_apex(result)
        for host in result.hosts.values():
            self.assess_host(host, result, hygiene, novel_names)

        ranked = sorted(result.hosts.values(), key=lambda h: h.risk, reverse=True)
        summary = {
            "hygiene": hygiene,
            "top_risks": [
                {"name": h.name, "risk": h.risk, "reasons": h.risk_reasons}
                for h in ranked if h.risk > 0
            ][:10],
            "high_risk_count": sum(1 for h in result.hosts.values() if h.risk >= 60),
        }
        result.meta["risk"] = summary
        return summary
