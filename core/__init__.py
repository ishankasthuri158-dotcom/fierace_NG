"""Core shared types for Fierce-NG: configuration, data models, orchestration."""
from .config import ScanConfig
from .models import Host, ScanResult

__all__ = ["ScanConfig", "Host", "ScanResult", "AdaptiveReconBrain"]


def __getattr__(name):
    # Lazy: arb imports dns_engine, which imports core.models -- loading arb
    # eagerly here made `import dns_engine` / `import graph` a circular import.
    if name == "AdaptiveReconBrain":
        from .arb import AdaptiveReconBrain
        return AdaptiveReconBrain
    raise AttributeError(f"module 'core' has no attribute {name!r}")
