"""Property graph of the attack surface (Day 6).

Builds a small property graph from a :class:`ScanResult`:

  nodes:  domain, subdomain, ip, cname-target/provider
  edges:  resolves_to (host -> ip), cname_to (host -> target),
          subdomain_of (host -> domain)

Kept dependency-free (no networkx) so it installs cleanly on Kali. Exports to
GraphML (opens in Gephi/yEd) and a JSON node-link format (easy to load into
Neo4j via APOC or a small loader).
"""
from __future__ import annotations

import json
from xml.sax.saxutils import escape


class AttackGraph:
    def __init__(self):
        self.nodes: dict[str, dict] = {}   # id -> attributes
        self.edges: list[tuple[str, str, str]] = []  # (src, dst, relation)

    def add_node(self, node_id: str, ntype: str, **attrs) -> None:
        node = self.nodes.setdefault(node_id, {"type": ntype})
        node.update(attrs)

    def add_edge(self, src: str, dst: str, relation: str) -> None:
        edge = (src, dst, relation)
        if edge not in self.edges:
            self.edges.append(edge)

    @classmethod
    def from_result(cls, result) -> "AttackGraph":
        g = cls()
        g.add_node(result.domain, "domain", risk=0)
        for host in result.hosts.values():
            g.add_node(host.name, "subdomain", risk=host.risk,
                       sources=",".join(sorted(host.sources)))
            if host.name != result.domain:
                g.add_edge(host.name, result.domain, "subdomain_of")
            for ip in host.ips:
                g.add_node(ip, "ip")
                g.add_edge(host.name, ip, "resolves_to")
            if host.cname:
                g.add_node(host.cname, "cname")
                g.add_edge(host.name, host.cname, "cname_to")
        return g

    # -- exporters ---------------------------------------------------------
    def to_node_link(self) -> dict:
        return {
            "nodes": [{"id": nid, **attrs} for nid, attrs in self.nodes.items()],
            "links": [{"source": s, "target": d, "relation": r} for s, d, r in self.edges],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_node_link(), indent=2)

    def to_graphml(self) -> str:
        keys = (
            '<key id="type" for="node" attr.name="type" attr.type="string"/>'
            '<key id="risk" for="node" attr.name="risk" attr.type="int"/>'
            '<key id="sources" for="node" attr.name="sources" attr.type="string"/>'
            '<key id="relation" for="edge" attr.name="relation" attr.type="string"/>'
        )
        parts = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
            keys,
            '<graph edgedefault="directed">',
        ]
        for nid, attrs in self.nodes.items():
            parts.append(f'<node id="{escape(nid)}">')
            parts.append(f'<data key="type">{escape(str(attrs.get("type","")))}</data>')
            parts.append(f'<data key="risk">{int(attrs.get("risk", 0))}</data>')
            if attrs.get("sources"):
                parts.append(f'<data key="sources">{escape(str(attrs["sources"]))}</data>')
            parts.append("</node>")
        for i, (s, d, r) in enumerate(self.edges):
            parts.append(f'<edge id="e{i}" source="{escape(s)}" target="{escape(d)}">')
            parts.append(f'<data key="relation">{escape(r)}</data>')
            parts.append("</edge>")
        parts.append("</graph></graphml>")
        return "\n".join(parts)

    def stats(self) -> dict:
        by_type: dict[str, int] = {}
        for attrs in self.nodes.values():
            by_type[attrs["type"]] = by_type.get(attrs["type"], 0) + 1
        return {"nodes": len(self.nodes), "edges": len(self.edges), "by_type": by_type}
