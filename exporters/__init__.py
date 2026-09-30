"""Exporters: JSON / CSV / HTML, GraphML/Neo4j, diff/alerts, signed manifest."""
from __future__ import annotations

import os

from .formats import to_json, to_csv, to_html
from .manifest import build_manifest, verify_manifest, sha256
from .diff import load_previous, diff_scans, novel_names_from_previous


def export_all(result, graph=None, outdir: str = "out", prefix: str | None = None) -> dict[str, str]:
    """Write every artifact for a scan; return ``{artifact: path}``."""
    os.makedirs(outdir, exist_ok=True)
    prefix = prefix or result.domain.replace(".", "_")
    base = os.path.join(outdir, prefix)

    # Manifest first so the result carries it (HTML footer shows the hash).
    result.manifest = build_manifest(result, result.meta.get("config", {}))

    written: dict[str, str] = {}

    def _write(suffix: str, content: str, key: str) -> None:
        path = f"{base}.{suffix}"
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content)
        written[key] = path

    _write("json", to_json(result), "json")
    _write("csv", to_csv(result), "csv")
    _write("html", to_html(result), "html")

    import json
    _write("manifest.json", json.dumps(result.manifest, indent=2), "manifest")

    if graph is not None:
        _write("graphml", graph.to_graphml(), "graphml")
        _write("graph.json", graph.to_json(), "graph")
        from graph.view import graph_to_html
        _write("graph.html", graph_to_html(graph, f"Fierce-NG attack graph — {result.domain}"), "graph_view")

    return written


__all__ = [
    "export_all",
    "to_json",
    "to_csv",
    "to_html",
    "build_manifest",
    "verify_manifest",
    "sha256",
    "load_previous",
    "diff_scans",
    "novel_names_from_previous",
]
