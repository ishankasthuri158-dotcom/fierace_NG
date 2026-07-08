"""Adaptive Recon Brain -- ARB (Day 7).

The orchestrator that ties every module together. It decides *how* to scan
(passive-first vs active-augmented vs hybrid), then runs the modules in the
right order under one shared stealth budget:

    apex records + wildcard   (always -- cheap, needed for hygiene scoring)
    passive OSINT collectors  (passive / hybrid / auto)
    active discovery: AXFR, ML-ranked + wordlist brute-force  (active / hybrid)
    resolve everything discovered
    risk scoring + attack graph
    signed run manifest

In ``auto`` mode the brain starts passive, measures yield, and escalates to
active discovery only if passive did not surface enough resolved hosts -- the
"adaptive, passive-first" behaviour from the proposal.
"""
from __future__ import annotations

import time

from rich.console import Console
from rich.progress import track

from core.config import ScanConfig
from core.models import Host, ScanResult
from stealth import StealthResolver
from dns_engine import DNSEngine, bruteforce_subdomains, load_wordlist
from dns_engine.engine import scan_apex
from collectors import gather
from ml_predictor import SubdomainPredictor
from graph import RiskAssessor, AttackGraph

# Below this many resolved hosts, auto mode escalates from passive to active.
AUTO_ESCALATE_THRESHOLD = 5


class AdaptiveReconBrain:
    def __init__(self, config: ScanConfig, quiet: bool = False):
        config.validate()
        self.config = config
        self.quiet = quiet
        self.console = Console(quiet=quiet)
        self.resolver = StealthResolver(
            resolvers=config.resolvers,
            qps=config.qps,
            jitter=config.jitter,
            timeout=config.timeout,
            max_errors=config.max_errors,
        )
        self.engine = DNSEngine(self.resolver, record_types=config.record_types)

    def _log(self, msg: str) -> None:
        if not self.quiet:
            self.console.print(msg)

    # -- mode decision -----------------------------------------------------
    def decide_plan(self) -> dict:
        """Translate the configured mode into a concrete module plan."""
        mode = self.config.mode
        if mode == "passive":
            return {"passive": True, "active": False, "escalate": False}
        if mode == "active":
            return {"passive": False, "active": True, "escalate": False}
        if mode == "hybrid":
            return {"passive": True, "active": True, "escalate": False}
        # auto: passive-first, escalate if needed
        return {"passive": True, "active": False, "escalate": True}

    # -- phases ------------------------------------------------------------
    def _run_passive(self, result: ScanResult) -> None:
        self._log("[bold cyan]› Passive OSINT collectors[/bold cyan]")
        found = gather(
            result.domain,
            use_crtsh=self.config.use_crtsh,
            use_shodan=self.config.use_shodan,
        )
        for source, names in found.items():
            for name in names:
                result.add_name(name, source)
            self._log(f"  {source:8} → {len(names)} names")

    def _candidate_labels(self) -> list[str]:
        labels = load_wordlist(self.config.wordlist)
        if self.config.use_ml:
            self._log("[bold cyan]› ML predictor ranking candidates[/bold cyan]")
            predictor = SubdomainPredictor(model_path=self.config.ml_model)
            ml_labels = predictor.predict(n=self.config.ml_candidates)
            # ML candidates first (ranked), then wordlist, de-duplicated.
            seen: set[str] = set()
            merged = []
            for label in ml_labels + labels:
                if label not in seen:
                    seen.add(label)
                    merged.append(label)
            self._log(f"  ML added {len(set(ml_labels) - set(labels))} new candidates")
            return merged
        return labels

    def _run_active(self, result: ScanResult) -> None:
        self._log("[bold cyan]› Active DNS discovery[/bold cyan]")
        # AXFR (rare but high value)
        if self.config.try_axfr:
            axfr_names = self.engine.try_axfr(result.domain)
            if axfr_names:
                result.meta["axfr_names"] = axfr_names
                self._log(f"  [red]AXFR succeeded![/red] {len(axfr_names)} names disclosed")
                for name in axfr_names:
                    result.add_name(name, "axfr")

        # Brute-force with ML-ranked + wordlist candidates
        candidates = self._candidate_labels()
        hits = bruteforce_subdomains(
            result.domain, self.resolver, candidates=candidates, quiet=self.quiet
        )
        for host in hits:
            result.add_host(host)

    def _resolve_all(self, result: ScanResult) -> None:
        """Resolve every discovered-but-unresolved name to enrich records."""
        pending = [h for h in result.hosts.values() if not h.resolved]
        if not pending:
            return
        self._log(f"[bold cyan]› Resolving {len(pending)} discovered names[/bold cyan]")
        use_bar = not self.quiet and self.console.is_terminal
        iterator = track(pending, description="Resolving...") if use_bar else pending
        for host in iterator:
            if self.resolver.aborted():
                break
            enriched = self.engine.resolve_host(host.name)
            enriched.sources = host.sources
            result.hosts[host.name] = enriched

    # -- driver ------------------------------------------------------------
    def run(self, novel_names: set[str] | None = None) -> ScanResult:
        started = time.time()
        cfg = self.config
        result = ScanResult(domain=cfg.domain, mode=cfg.mode)
        plan = self.decide_plan()

        self._log(f"\n[bold green]Fierce-NG[/bold green] scanning [cyan]{cfg.domain}[/cyan] "
                  f"(mode: [yellow]{cfg.mode}[/yellow])")

        # Apex + wildcard (always).
        scan_apex(self.engine, result, detect_wildcard=True)
        result.add_name(cfg.domain, "apex")
        if result.wildcard:
            self._log("  [red]⚠ Wildcard DNS detected — brute-force results filtered by resolution[/red]")

        if plan["passive"]:
            self._run_passive(result)
            # Resolve the high-value OSINT names first, before any brute-force
            # can consume the stealth/error budget.
            self._resolve_all(result)

        # Auto-escalation: did passive find enough resolved hosts?
        if plan["escalate"]:
            resolved = len(result.resolved_hosts)
            if resolved < AUTO_ESCALATE_THRESHOLD:
                self._log(f"  [yellow]Auto: only {resolved} resolved hosts — "
                          f"escalating to active discovery[/yellow]")
                plan["active"] = True
            else:
                self._log(f"  [green]Auto: {resolved} resolved hosts — passive sufficient[/green]")

        if plan["active"] or cfg.brute:
            self._run_active(result)
            self._resolve_all(result)

        # Risk + graph.
        self._log("[bold cyan]› Risk scoring[/bold cyan]")
        assessor = RiskAssessor(self.engine)
        assessor.assess(result, novel_names=novel_names)
        graph = AttackGraph.from_result(result)

        # Meta.
        result.meta.update({
            "duration_sec": round(time.time() - started, 2),
            "config": cfg.to_dict(),
            "stealth_stats": self.resolver.stats,
            "counts": {
                "hosts": len(result.hosts),
                "resolved": len(result.resolved_hosts),
            },
            "graph": graph.stats(),
        })
        self._result_graph = graph  # exposed for exporters
        return result
