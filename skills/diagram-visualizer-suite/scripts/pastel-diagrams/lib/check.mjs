// Layout check: finds crossing edges, edges running through other nodes, overlapping labels,
// clipped labels and too many nodes, so an agent can fix a diagram without looking at the image.

export const MAX_NODES = 12;

// Runs inside the page (passed to page.evaluate). `svg` is the rendered <svg>, `kind` the diagram kind.
export function measureLayout(svg, kind) {
  const box = (el) => { const b = el.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; };
  const name = (el) => {
    const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), parts = [];
    while (w.nextNode()) parts.push(w.currentNode.data.trim());
    return parts.filter(Boolean).join(" ").replace(/\s+/g, " ").slice(0, 40) || "(unnamed)";
  };
  const overlap = (a, b, pad = 0) => {
    const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x) - pad, h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y) - pad;
    return w > 0 && h > 0 ? w * h : 0;
  };
  const inside = (p, b, m = 0) => p.x > b.x - m && p.x < b.x + b.w + m && p.y > b.y - m && p.y < b.y + b.h + m;
  const r = { kind, nodes: 0, edges: 0, crossings: [], throughNode: [], overlaps: [], clipped: [] };

  // ---- nodes
  let nodes = [];
  if (kind === "sequence") {
    r.nodes = new Set([...svg.querySelectorAll("text.actor")].map(name)).size;
  } else if (kind === "mindmap") {
    nodes = [...svg.querySelectorAll("g.mindmap-node, g.node")];
  } else if (kind === "timeline") {
    nodes = [...svg.querySelectorAll("g.taskWrapper, g.eventWrapper")];
  } else {
    nodes = [...svg.querySelectorAll("g.node")].filter((n) => !n.closest("g.cluster") || n.closest("g.nodes"));
  }
  const N = nodes.map((el) => ({ el, name: name(el), b: box(el) })).filter((n) => n.b.w > 0);
  if (kind !== "sequence") r.nodes = N.filter((n) => !/state-start|state-end|root_start|root_end/.test(n.el.getAttribute("id") || "") && n.name !== "(unnamed)").length;

  // ---- clipped labels: label content larger than its box, or content outside the canvas
  for (const n of N) {
    for (const fo of n.el.querySelectorAll("foreignObject")) {
      const inner = fo.firstElementChild;
      if (!inner) continue;
      const fw = fo.width.baseVal.value, fh = fo.height.baseVal.value;
      if (inner.scrollWidth > fw + 2 || inner.scrollHeight > fh + 2) r.clipped.push(`label "${n.name}" is cut off inside its card`);
    }
    const shape = n.el.querySelector(":scope > rect, :scope > polygon, :scope > path, :scope > g > rect, :scope > g > path");
    const lab = n.el.querySelector(".label, foreignObject");
    if (shape && lab && shape.tagName === "rect" && kind !== "mindmap") {
      const s = box(shape), l = box(lab);
      if (l.w > s.w + 4) r.clipped.push(`label "${n.name}" is wider than its card`);
    }
  }
  // Text and cards that stick out of the image (lines running to the edge are fine).
  const frame = box(svg);
  for (const el of svg.querySelectorAll("g.node, g.edgeLabel, g.cluster-label, text, foreignObject")) {
    const b = box(el);
    if (b.w && (b.x < frame.x - 1 || b.y < frame.y - 1 || b.x + b.w > frame.x + frame.w + 1 || b.y + b.h > frame.y + frame.h + 1)) {
      r.clipped.push(`"${name(el)}" sticks out of the image edge`);
      break;
    }
  }

  if (kind === "sequence") {
    const T = [...svg.querySelectorAll(".messageText, .noteText")].map((el) => ({ name: name(el), b: box(el) }));
    for (let i = 0; i < T.length; i++) for (let j = i + 1; j < T.length; j++)
      if (overlap(T[i].b, T[j].b, 1) > 4) r.overlaps.push(`"${T[i].name}" overlaps "${T[j].name}"`);
    return r;
  }
  if (kind === "mindmap" || kind === "timeline") {
    for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++)
      if (!N[i].el.contains(N[j].el) && !N[j].el.contains(N[i].el) && overlap(N[i].b, N[j].b, 1) > 4) r.overlaps.push(`"${N[i].name}" overlaps "${N[j].name}"`);
    return r;
  }

  // ---- edges as sampled polylines in screen coordinates
  const paths = [...svg.querySelectorAll("g.edgePaths > path, path.flowchart-link, path.transition, path.relationshipLine")]
    .filter((p, i, a) => a.indexOf(p) === i && p.getTotalLength() > 0);
  const nearest = (p) => {
    let best = null, d = 1e9;
    for (const n of N) {
      const dx = Math.max(n.b.x - p.x, 0, p.x - n.b.x - n.b.w), dy = Math.max(n.b.y - p.y, 0, p.y - n.b.y - n.b.h), dd = Math.hypot(dx, dy);
      if (dd < d) { d = dd; best = n; }
    }
    return d < 30 ? best : null;
  };
  const E = paths.map((p) => {
    const len = p.getTotalLength(), m = p.getScreenCTM(), pts = [];
    for (let s = 0; s <= len; s += 3) { const q = p.getPointAtLength(Math.min(s, len)); pts.push(new DOMPoint(q.x, q.y).matrixTransform(m)); }
    const end = p.getPointAtLength(len); pts.push(new DOMPoint(end.x, end.y).matrixTransform(m));
    const from = nearest(pts[0]), to = nearest(pts[pts.length - 1]);
    return { pts, from, to, name: `${from ? from.name : "?"} → ${to ? to.name : "?"}` };
  });
  r.edges = E.length;

  const seg = (a, b, c, d) => {
    const den = (b.x - a.x) * (d.y - c.y) - (b.y - a.y) * (d.x - c.x);
    if (Math.abs(den) < 1e-9) return null;
    const t = ((c.x - a.x) * (d.y - c.y) - (c.y - a.y) * (d.x - c.x)) / den, u = ((c.x - a.x) * (b.y - a.y) - (c.y - a.y) * (b.x - a.x)) / den;
    return t >= 0 && t <= 1 && u >= 0 && u <= 1 ? { x: a.x + t * (b.x - a.x), y: a.y + t * (b.y - a.y) } : null;
  };
  const nearEnds = (p, e, m = 14) => [e.pts[0], e.pts[e.pts.length - 1]].some((q) => Math.hypot(q.x - p.x, q.y - p.y) < m);
  const inEndNode = (p, e) => [e.from, e.to].some((n) => n && inside(p, n.b, 6));
  for (let i = 0; i < E.length; i++) for (let j = i + 1; j < E.length; j++) {
    const A = E[i], B = E[j];
    let hit = null;
    for (let a = 1; a < A.pts.length && !hit; a++) for (let b = 1; b < B.pts.length && !hit; b++) {
      const p = seg(A.pts[a - 1], A.pts[a], B.pts[b - 1], B.pts[b]);
      if (p && !nearEnds(p, A) && !nearEnds(p, B) && !inEndNode(p, A) && !inEndNode(p, B)) hit = p;
    }
    if (hit) r.crossings.push(`edge "${A.name}" crosses edge "${B.name}"`);
  }
  for (const e of E) for (const n of N) {
    if (n === e.from || n === e.to) continue;
    const inner = { x: n.b.x + 4, y: n.b.y + 4, w: n.b.w - 8, h: n.b.h - 8 };
    if (inner.w > 0 && e.pts.some((p) => inside(p, inner))) r.throughNode.push(`edge "${e.name}" runs through "${n.name}"`);
  }

  // ---- overlapping labels: edge labels against each other and against nodes
  const L = [...svg.querySelectorAll("g.edgeLabel")].filter((el) => name(el) !== "(unnamed)")
    .map((el) => ({ name: name(el), b: box(el.querySelector("p") || el.querySelector("span, text, foreignObject") || el) })).filter((l) => l.b.w > 0);
  for (let i = 0; i < L.length; i++) {
    for (let j = i + 1; j < L.length; j++) if (overlap(L[i].b, L[j].b) > 4) r.overlaps.push(`edge label "${L[i].name}" overlaps edge label "${L[j].name}"`);
    for (const n of N) if (overlap(L[i].b, n.b, 1) > 4) r.overlaps.push(`edge label "${L[i].name}" overlaps "${n.name}"`);
  }
  for (let i = 0; i < N.length; i++) for (let j = i + 1; j < N.length; j++)
    if (!N[i].el.contains(N[j].el) && !N[j].el.contains(N[i].el) && overlap(N[i].b, N[j].b, 1) > 4) r.overlaps.push(`"${N[i].name}" overlaps "${N[j].name}"`);
  return r;
}

export function problems(r) {
  return [...r.crossings, ...r.throughNode, ...r.overlaps, ...r.clipped];
}

export function warnings(r) {
  const max = r.kind === "mindmap" || r.kind === "timeline" ? MAX_NODES + 8 : r.kind === "sequence" ? 6 : MAX_NODES;
  return r.nodes > max ? [`${r.nodes} ${r.kind === "sequence" ? "participants" : "nodes"} (more than ${max}); consider splitting the diagram`] : [];
}

export function summary(r) {
  const p = problems(r).length, w = warnings(r).length;
  const parts = [`${r.nodes} ${r.kind === "sequence" ? "participants" : "nodes"}`];
  if (r.edges) parts.push(`${r.edges} edges`);
  parts.push(`${r.crossings.length} crossings`);
  if (r.throughNode.length) parts.push(`${r.throughNode.length} through nodes`);
  parts.push(`${r.overlaps.length} overlaps`, `${r.clipped.length} clipped`);
  return `${p || w ? "WARN" : "ok  "} ${parts.join(", ")}`;
}
