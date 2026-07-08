"""Scan configuration for Fierce-NG.

A single ``ScanConfig`` object is threaded through every module so that a run is
fully described (and therefore reproducible) by one serialisable structure.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict


# Public resolvers used by the stealth orchestrator for rotation.
DEFAULT_RESOLVERS = [
    "1.1.1.1",        # Cloudflare
    "8.8.8.8",        # Google
    "9.9.9.9",        # Quad9
    "208.67.222.222",  # OpenDNS
    "8.26.56.26",     # Comodo
]

VALID_MODES = ("passive", "active", "hybrid", "auto")


@dataclass
class ScanConfig:
    """Everything needed to describe and reproduce a scan."""

    domain: str
    mode: str = "hybrid"                      # passive | active | hybrid | auto

    # --- Active DNS engine ---
    record_types: list[str] = field(
        default_factory=lambda: ["A", "AAAA", "MX", "NS", "TXT", "CAA", "SRV"]
    )
    try_axfr: bool = True
    detect_dangling: bool = True

    # --- Brute force ---
    brute: bool = False
    wordlist: str | None = None               # path; None -> built-in list

    # --- Passive OSINT collectors ---
    use_crtsh: bool = True
    use_shodan: bool = False                  # requires SHODAN_API_KEY

    # --- ML predictor ---
    use_ml: bool = False
    ml_model: str | None = None               # path to trained model json
    ml_candidates: int = 200                  # how many predictions to verify

    # --- Stealth orchestrator ---
    qps: float = 10.0                         # max queries/sec per resolver
    jitter: float = 0.15                      # +/- seconds of random delay
    resolvers: list[str] = field(default_factory=lambda: list(DEFAULT_RESOLVERS))
    max_errors: int = 250                     # hard safety cap (sustained failure)
    timeout: float = 5.0

    def validate(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode must be one of {VALID_MODES}, got {self.mode!r}")
        if not self.domain or "." not in self.domain:
            raise ValueError(f"invalid domain: {self.domain!r}")

    def to_dict(self) -> dict:
        return asdict(self)
