"""Interactive HTML viewer for the attack-surface graph.

Renders the node-link JSON written by :meth:`AttackGraph.to_json` (the
``*.graph.json`` artifact) as a single self-contained HTML page: a
force-directed layout drawn in SVG with plain JavaScript. No external
libraries or CDN, so it works offline on Kali like the rest of Fierce-NG.

Usage:
    python -m graph.view out/example_com.graph.json          # writes + opens .graph.html
    python -m graph.view out/example_com.graph.json -o g.html --no-open
    python -m graph.view --demo                               # sample graph, no scan needed

In the page: drag nodes, scroll to zoom, drag the background to pan, hover a
node for its details, and type in the search box to highlight hosts.
"""
from __future__ import annotations

import json
import os
import sys
import webbrowser

from .graph import AttackGraph


def render_html(node_link: dict, title: str = "Fierce-NG attack graph") -> str:
    """Return a standalone HTML page that draws ``node_link`` interactively."""
    # Escape "</" so hostnames can never close the <script> block early.
    data = json.dumps(node_link).replace("</", "<\\/")
    safe_title = (title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    return _TEMPLATE.replace("__TITLE__", safe_title).replace("__DATA__", data)


def graph_to_html(graph: AttackGraph, title: str = "Fierce-NG attack graph") -> str:
    return render_html(graph.to_node_link(), title=title)


def demo_graph() -> AttackGraph:
    """A small hand-made graph for trying the viewer without running a scan."""
    g = AttackGraph()
    g.add_node("example.com", "domain", risk=0)
    hosts = [
        ("www.example.com", 5, "crtsh,brute", ["93.184.216.34"], None),
        ("mail.example.com", 15, "crtsh", ["93.184.216.40"], None),
        ("admin.example.com", 40, "brute", ["93.184.216.50"], None),
        ("dev.example.com", 45, "ml", ["10.0.0.12"], None),
        ("jenkins.example.com", 50, "crtsh,ml", ["10.0.0.12"], None),
        ("api.example.com", 10, "crtsh,shodan", ["93.184.216.34"], None),
        ("blog.example.com", 85, "crtsh", [], "old-bucket.s3.amazonaws.com"),
        ("cdn.example.com", 0, "brute", [], "example.cloudfront.net"),
        ("staging.example.com", 65, "ml", ["10.0.0.20"], None),
    ]
    for name, risk, sources, ips, cname in hosts:
        g.add_node(name, "subdomain", risk=risk, sources=sources)
        g.add_edge(name, "example.com", "subdomain_of")
        for ip in ips:
            g.add_node(ip, "ip")
            g.add_edge(name, ip, "resolves_to")
        if cname:
            g.add_node(cname, "cname")
            g.add_edge(name, cname, "cname_to")
    return g


def _main(argv: list[str]) -> int:
    args = [a for a in argv if not a.startswith("-")]
    no_open = "--no-open" in argv
    out = None
    if "-o" in argv:
        out = argv[argv.index("-o") + 1]
        args = [a for a in args if a != out]

    if "--demo" in argv:
        node_link = demo_graph().to_node_link()
        title = "Fierce-NG attack graph (demo)"
        out = out or "demo.graph.html"
    elif args:
        with open(args[0], "r", encoding="utf-8") as fh:
            node_link = json.load(fh)
        domain = next((n["id"] for n in node_link.get("nodes", []) if n.get("type") == "domain"), "")
        title = f"Fierce-NG attack graph — {domain}" if domain else "Fierce-NG attack graph"
        out = out or os.path.splitext(args[0])[0] + ".html"   # x.graph.json -> x.graph.html
    else:
        print(__doc__)
        return 1

    with open(out, "w", encoding="utf-8") as fh:
        fh.write(render_html(node_link, title=title))
    print(f"Wrote {out} ({len(node_link.get('nodes', []))} nodes, {len(node_link.get('links', []))} edges)")

    if not no_open:
        webbrowser.open("file://" + os.path.abspath(out))
    return 0


_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
  :root {
    --bg: #f7f7f5; --panel: #ffffff; --text: #1f2328; --muted: #6b7280;
    --border: #d9dbde; --edge: #b9bdc4;
    --domain: #1f2328; --ip: #8b95a3; --cname: #7c5cc4;
    --low: #2e9e5b; --med: #d9951a; --high: #d1453b;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16181c; --panel: #1f2227; --text: #e6e8eb; --muted: #9aa2ad;
      --border: #33373e; --edge: #4a5059;
      --domain: #e6e8eb; --ip: #7d8794; --cname: #a58bea;
      --low: #3fbf74; --med: #e9ab3a; --high: #ef5f55;
    }
  }
  * { box-sizing: border-box; }
  html, body { margin: 0; height: 100%; background: var(--bg); color: var(--text);
    font: 14px/1.4 system-ui, -apple-system, "Segoe UI", sans-serif; }
  header { display: flex; flex-wrap: wrap; gap: 12px 20px; align-items: center;
    padding: 12px 16px; border-bottom: 1px solid var(--border); background: var(--panel); }
  h1 { font-size: 16px; margin: 0; font-weight: 600; }
  .stats { color: var(--muted); }
  input { font: inherit; padding: 5px 9px; border: 1px solid var(--border); border-radius: 6px;
    background: var(--bg); color: var(--text); min-width: 180px; }
  .legend { display: flex; flex-wrap: wrap; gap: 6px 14px; color: var(--muted); font-size: 13px; }
  .legend span { display: inline-flex; align-items: center; gap: 6px; }
  .dot { width: 11px; height: 11px; border-radius: 50%; display: inline-block; }
  #wrap { position: absolute; top: var(--head, 58px); left: 0; right: 0; bottom: 0; }
  svg { width: 100%; height: 100%; display: block; cursor: grab; }
  svg.panning { cursor: grabbing; }
  .edge { stroke: var(--edge); stroke-width: 1.2; }
  .edge.cname_to { stroke: var(--cname); stroke-dasharray: 4 3; }
  .edge.resolves_to { stroke-dasharray: 1 3; }
  .node circle { stroke: var(--panel); stroke-width: 1.5; cursor: pointer; }
  .node text { font-size: 11px; fill: var(--text); pointer-events: none;
    paint-order: stroke; stroke: var(--bg); stroke-width: 3px; }
  .dim { opacity: 0.15; }
  .hit circle { stroke: var(--text); stroke-width: 3; }
  #tip { position: fixed; pointer-events: none; background: var(--panel); border: 1px solid var(--border);
    border-radius: 8px; padding: 8px 10px; font-size: 13px; box-shadow: 0 4px 14px rgba(0,0,0,.15);
    display: none; max-width: 320px; }
  #tip b { display: block; margin-bottom: 2px; word-break: break-all; }
  #tip .k { color: var(--muted); }
</style>
</head>
<body>
<header id="head">
  <h1>__TITLE__</h1>
  <span class="stats" id="stats"></span>
  <input id="q" type="search" placeholder="Search host or IP…">
  <div class="legend">
    <span><i class="dot" style="background:var(--domain)"></i>domain</span>
    <span><i class="dot" style="background:var(--low)"></i>risk &lt;30</span>
    <span><i class="dot" style="background:var(--med)"></i>risk 30–59</span>
    <span><i class="dot" style="background:var(--high)"></i>risk ≥60</span>
    <span><i class="dot" style="background:var(--ip)"></i>IP</span>
    <span><i class="dot" style="background:var(--cname)"></i>CNAME target</span>
  </div>
</header>
<div id="wrap"><svg id="svg"><g id="view"><g id="edges"></g><g id="nodes"></g></g></svg></div>
<div id="tip"></div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function () {
  const data = JSON.parse(document.getElementById("data").textContent);
  const NS = "http://www.w3.org/2000/svg";
  const svg = document.getElementById("svg"), view = document.getElementById("view");
  const tip = document.getElementById("tip");
  document.documentElement.style.setProperty("--head", document.getElementById("head").offsetHeight + "px");

  const nodes = data.nodes.map(n => Object.assign({}, n));
  const byId = new Map(nodes.map(n => [n.id, n]));
  const links = data.links.filter(l => byId.has(l.source) && byId.has(l.target))
    .map(l => ({ s: byId.get(l.source), t: byId.get(l.target), relation: l.relation }));
  const degree = new Map(nodes.map(n => [n.id, 0]));
  links.forEach(l => { degree.set(l.s.id, degree.get(l.s.id) + 1); degree.set(l.t.id, degree.get(l.t.id) + 1); });

  const counts = {};
  nodes.forEach(n => counts[n.type] = (counts[n.type] || 0) + 1);
  const high = nodes.filter(n => n.type === "subdomain" && (n.risk || 0) >= 60).length;
  document.getElementById("stats").textContent =
    `${counts.subdomain || 0} hosts · ${counts.ip || 0} IPs · ${counts.cname || 0} CNAMEs · ${high} high-risk`;

  function color(n) {
    if (n.type === "domain") return "var(--domain)";
    if (n.type === "ip") return "var(--ip)";
    if (n.type === "cname") return "var(--cname)";
    const r = n.risk || 0;
    return r >= 60 ? "var(--high)" : r >= 30 ? "var(--med)" : "var(--low)";
  }
  function radius(n) {
    if (n.type === "domain") return 14;
    if (n.type === "subdomain") return 6 + Math.min(8, (n.risk || 0) / 12);
    return 5;
  }
  function label(n) {
    if (n.type !== "subdomain") return n.id;
    const dom = nodes.find(x => x.type === "domain");
    return dom && n.id.endsWith("." + dom.id) ? n.id.slice(0, -dom.id.length - 1) : n.id;
  }

  // Initial positions: spread on a circle so the layout starts untangled.
  const W = () => svg.clientWidth, H = () => svg.clientHeight;
  nodes.forEach((n, i) => {
    const a = (i / nodes.length) * Math.PI * 2, r = n.type === "domain" ? 0 : 150 + (i % 5) * 30;
    n.x = W() / 2 + Math.cos(a) * r; n.y = H() / 2 + Math.sin(a) * r; n.vx = 0; n.vy = 0;
  });

  // Build SVG elements.
  const edgeEls = links.map(l => {
    const e = document.createElementNS(NS, "line");
    e.setAttribute("class", "edge " + l.relation);
    document.getElementById("edges").appendChild(e);
    return e;
  });
  const showLabels = nodes.length <= 400;
  const nodeEls = nodes.map(n => {
    const g = document.createElementNS(NS, "g");
    g.setAttribute("class", "node");
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("r", radius(n)); c.setAttribute("fill", color(n));
    g.appendChild(c);
    if (showLabels || n.type === "domain" || (n.risk || 0) >= 60) {
      const t = document.createElementNS(NS, "text");
      t.setAttribute("x", radius(n) + 4); t.setAttribute("y", 4);
      t.textContent = label(n);
      g.appendChild(t);
    }
    g.addEventListener("pointerdown", ev => startDrag(ev, n));
    g.addEventListener("pointerenter", ev => showTip(ev, n));
    g.addEventListener("pointermove", moveTip);
    g.addEventListener("pointerleave", () => tip.style.display = "none");
    document.getElementById("nodes").appendChild(g);
    return g;
  });

  function esc(s) { return String(s).replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c])); }
  function showTip(ev, n) {
    let html = `<b>${esc(n.id)}</b><span class="k">type:</span> ${esc(n.type)}`;
    if (n.type === "subdomain") html += `<br><span class="k">risk:</span> ${n.risk || 0}/100`;
    if (n.sources) html += `<br><span class="k">sources:</span> ${esc(n.sources)}`;
    html += `<br><span class="k">links:</span> ${degree.get(n.id)}`;
    tip.innerHTML = html; tip.style.display = "block"; moveTip(ev);
  }
  function moveTip(ev) {
    const x = Math.min(ev.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + "px"; tip.style.top = (ev.clientY + 14) + "px";
  }

  // Force simulation: repulsion between all nodes, springs along edges,
  // a gentle pull to the centre. Cools down (alpha) so it settles.
  let alpha = 1;
  function tick() {
    const cx = W() / 2, cy = H() / 2;
    for (let i = 0; i < nodes.length; i++) {
      const a = nodes[i];
      for (let j = i + 1; j < nodes.length; j++) {
        const b = nodes[j];
        let dx = a.x - b.x, dy = a.y - b.y, d2 = dx * dx + dy * dy || 0.01;
        if (d2 > 90000) continue;
        const f = 900 / d2 * alpha, d = Math.sqrt(d2);
        dx /= d; dy /= d;
        a.vx += dx * f; a.vy += dy * f; b.vx -= dx * f; b.vy -= dy * f;
      }
    }
    links.forEach(l => {
      const rest = l.relation === "subdomain_of" ? 110 : 45;
      let dx = l.t.x - l.s.x, dy = l.t.y - l.s.y, d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      const f = (d - rest) * 0.02 * alpha;
      dx /= d; dy /= d;
      l.s.vx += dx * f; l.s.vy += dy * f; l.t.vx -= dx * f; l.t.vy -= dy * f;
    });
    nodes.forEach(n => {
      n.vx += (cx - n.x) * 0.002 * alpha; n.vy += (cy - n.y) * 0.002 * alpha;
      if (n === dragging) { n.vx = n.vy = 0; return; }
      n.vx *= 0.6; n.vy *= 0.6; n.x += n.vx; n.y += n.vy;
    });
    alpha = Math.max(0, alpha * 0.985);
  }
  function draw() {
    links.forEach((l, i) => {
      const e = edgeEls[i];
      e.setAttribute("x1", l.s.x); e.setAttribute("y1", l.s.y);
      e.setAttribute("x2", l.t.x); e.setAttribute("y2", l.t.y);
    });
    nodes.forEach((n, i) => nodeEls[i].setAttribute("transform", `translate(${n.x},${n.y})`));
  }
  function loop() {
    if (alpha > 0.005) { tick(); draw(); }
    requestAnimationFrame(loop);
  }

  // Zoom and pan.
  let scale = 1, tx = 0, ty = 0;
  function applyView() { view.setAttribute("transform", `translate(${tx},${ty}) scale(${scale})`); }
  function toGraph(ev) {
    const r = svg.getBoundingClientRect();
    return { x: (ev.clientX - r.left - tx) / scale, y: (ev.clientY - r.top - ty) / scale };
  }
  svg.addEventListener("wheel", ev => {
    ev.preventDefault();
    const r = svg.getBoundingClientRect(), mx = ev.clientX - r.left, my = ev.clientY - r.top;
    const k = Math.exp(-ev.deltaY * 0.0015), ns = Math.min(5, Math.max(0.1, scale * k));
    tx = mx - (mx - tx) * ns / scale; ty = my - (my - ty) * ns / scale; scale = ns;
    applyView();
  }, { passive: false });

  let dragging = null, panning = null;
  function startDrag(ev, n) {
    ev.stopPropagation(); dragging = n; alpha = Math.max(alpha, 0.3);
    svg.setPointerCapture(ev.pointerId);
  }
  svg.addEventListener("pointerdown", ev => {
    panning = { x: ev.clientX - tx, y: ev.clientY - ty };
    svg.classList.add("panning"); svg.setPointerCapture(ev.pointerId);
  });
  svg.addEventListener("pointermove", ev => {
    if (dragging) { const p = toGraph(ev); dragging.x = p.x; dragging.y = p.y; alpha = Math.max(alpha, 0.1); draw(); }
    else if (panning) { tx = ev.clientX - panning.x; ty = ev.clientY - panning.y; applyView(); }
  });
  svg.addEventListener("pointerup", () => { dragging = null; panning = null; svg.classList.remove("panning"); });

  // Search: highlight matches and dim everything else.
  document.getElementById("q").addEventListener("input", ev => {
    const q = ev.target.value.trim().toLowerCase();
    nodes.forEach((n, i) => {
      const hit = q && n.id.toLowerCase().includes(q);
      nodeEls[i].classList.toggle("hit", !!hit);
      nodeEls[i].classList.toggle("dim", !!q && !hit);
    });
    links.forEach((l, i) => edgeEls[i].classList.toggle("dim", !!q));
  });

  for (let i = 0; i < 150; i++) tick();   // pre-settle so the first frame is readable
  draw(); loop();
})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
