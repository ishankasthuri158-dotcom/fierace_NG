"""Signed run manifest (Day 8) for reproducible, auditable scans.

Every run emits a manifest recording the tool version, timestamp, the exact
input configuration and a SHA-256 hash of the results. If a signing key is
present (``FIERCE_NG_SIGNING_KEY`` env var) the manifest is HMAC-SHA256 signed
so a third party can verify it was produced by whoever holds the key and has
not been altered -- the auditability requirement from the proposal's ethics
section.
"""
from __future__ import annotations

import os
import json
import time
import hashlib
import hmac

from core.version import __version__


def _canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256(obj) -> str:
    return hashlib.sha256(_canonical(obj)).hexdigest()


def build_manifest(result, config: dict, signing_key: str | None = None) -> dict:
    key = signing_key or os.environ.get("FIERCE_NG_SIGNING_KEY")
    result_hash = sha256(result.to_dict())
    config_hash = sha256(config)

    manifest = {
        "tool": "fierce-ng",
        "version": __version__,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "domain": result.domain,
        "mode": result.mode,
        "config_sha256": config_hash,
        "result_sha256": result_hash,
        "counts": result.meta.get("counts", {}),
        "signed": False,
    }
    if key:
        payload = _canonical({k: manifest[k] for k in sorted(manifest) if k != "signed"})
        manifest["signature_hmac_sha256"] = hmac.new(
            key.encode("utf-8"), payload, hashlib.sha256
        ).hexdigest()
        manifest["signed"] = True
    return manifest


def verify_manifest(manifest: dict, signing_key: str | None = None) -> bool:
    """Re-compute the HMAC and confirm it matches the stored signature."""
    key = signing_key or os.environ.get("FIERCE_NG_SIGNING_KEY")
    if not key or not manifest.get("signed"):
        return False
    stored = manifest.get("signature_hmac_sha256", "")
    payload = _canonical(
        {k: manifest[k] for k in sorted(manifest)
         if k not in ("signed", "signature_hmac_sha256")}
    )
    expected = hmac.new(key.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(stored, expected)
