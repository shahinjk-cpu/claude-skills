// Orthogonal edge routing with libavoid (https://www.adaptagrams.org/documentation/libavoid.html):
// Mermaid places the nodes, then every edge is re-routed between pins at the centre of a node side,
// with straight segments that avoid other nodes. The page then draws the routes with rounded corners.

let avoid = null;
async function lib() {
  if (!avoid) {
    const { AvoidLib } = await import("libavoid-js");
    await AvoidLib.load();
    avoid = AvoidLib.getInstance();
  }
  return avoid;
}

// Runs inside the page: node boxes and edge ends in screen coordinates.
export function collectGeometry(svg) {
  const box = (el) => { const b = el.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; };
  // Diamonds and circles have one attach point per side (the tip); cards can spread lines along a side.
  const nodes = [...svg.querySelectorAll("g.node")].map((el) => ({ el, b: box(el),
    point: !!el.querySelector(":scope > polygon, :scope > circle, :scope > g > circle") || /state-(start|end)/.test(el.id) }))
    .filter((n) => n.b.w > 0 && n.b.h > 0);
  const nearest = (p) => {
    let best = -1, d = 1e9;
    nodes.forEach((n, i) => {
      const dx = Math.max(n.b.x - p.x, 0, p.x - n.b.x - n.b.w), dy = Math.max(n.b.y - p.y, 0, p.y - n.b.y - n.b.h), dd = Math.hypot(dx, dy);
      if (dd < d) { d = dd; best = i; }
    });
    return d < 30 ? best : -1;
  };
  const edges = [...svg.querySelectorAll("path.flowchart-link, path.transition")].map((p, i) => {
    p.dataset.pdEdge = String(i);
    const len = p.getTotalLength(), m = p.getScreenCTM();
    const at = (s) => { const q = p.getPointAtLength(s); return new DOMPoint(q.x, q.y).matrixTransform(m); };
    // Mermaid stops a line 4px short of the node so a point arrowhead ends on the border.
    const trim = /pointEnd/.test(p.getAttribute("marker-end") || "") ? 4 : 0;
    return { i, id: p.dataset.id || "", from: nearest(at(0)), to: nearest(at(len)), trim };
  });
  return { nodes: nodes.map((n) => ({ ...n.b, point: n.point })), edges };
}

const SIDES = { top: [0.5, 0], right: [1, 0.5], bottom: [0.5, 1], left: [0, 0.5] };
const sideOf = (p, b) => {
  const d = { top: Math.abs(p.y - b.y), bottom: Math.abs(p.y - b.y - b.h), left: Math.abs(p.x - b.x), right: Math.abs(p.x - b.x - b.w) };
  return Object.keys(d).reduce((m, k) => (d[k] < d[m] ? k : m), "top");
};

async function newRouter(A, buffer, nudge) {
  const router = new A.Router(A.RouterFlag.OrthogonalRouting);
  router.setRoutingParameter(A.RoutingParameter.shapeBufferDistance, buffer);
  router.setRoutingParameter(A.RoutingParameter.idealNudgingDistance, nudge);
  router.setRoutingParameter(A.RoutingParameter.segmentPenalty, 40);
  router.setRoutingOption(A.RoutingOption.nudgeOrthogonalSegmentsConnectedToShapes, false); // keep lines on their pins
  router.setRoutingOption(A.RoutingOption.nudgeSharedPathsWithCommonEndPoint, true);
  return router;
}

// Removes small zigzags (a short middle segment between two parallel ones) by moving the
// segment before it in line with the segment after it; segments touching a node never move.
function straighten(pts, jog = 10) {
  for (let pass = 0; pass < 4; pass++) {
    let changed = false;
    for (let k = 1; k + 2 < pts.length; k++) {
      const a = pts[k], b = pts[k + 1], len = Math.hypot(b.x - a.x, b.y - a.y);
      if (len === 0 || len >= jog) continue;
      const vertical = Math.abs(a.x - b.x) < 0.5;
      if (k - 1 >= 1) { // segment pts[k-1]→pts[k] is not the first one: slide it onto the next segment's line
        if (vertical) { pts[k - 1].y = b.y; pts[k].y = b.y; } else { pts[k - 1].x = b.x; pts[k].x = b.x; }
      } else if (k + 2 < pts.length - 1) { // otherwise slide the segment after it, unless that one is the last
        if (vertical) { pts[k + 1].y = a.y; pts[k + 2].y = a.y; } else { pts[k + 1].x = a.x; pts[k + 2].x = a.x; }
      } else continue;
      changed = true;
    }
    pts = pts.filter((q, i, arr) => i === 0 || Math.hypot(q.x - arr[i - 1].x, q.y - arr[i - 1].y) > 0.5)
      .filter((q, i, arr) => i === 0 || i === arr.length - 1 ||
        !((Math.abs(arr[i - 1].x - q.x) < 0.5 && Math.abs(q.x - arr[i + 1].x) < 0.5) || (Math.abs(arr[i - 1].y - q.y) < 0.5 && Math.abs(q.y - arr[i + 1].y) < 0.5)));
    if (!changed) break;
  }
  return pts;
}

// Runs in Node: one route (list of screen points) per routable edge.
// Pass 1 routes every line to a side centre to find which side each line uses.
// Pass 2 spreads the lines on each side evenly: one line sits at the centre, k lines at 1/(k+1) ... k/(k+1),
// ordered by where they go so they do not cross; once a side is full (gap < minGap) lines share points.
export async function routeEdges({ nodes, edges }, { buffer = 14, nudge = 12, minGap = 10 } = {}) {
  const A = await lib(), D = A.ConnDirFlag;
  const DIR = { top: D.ConnDirUp, right: D.ConnDirRight, bottom: D.ConnDirDown, left: D.ConnDirLeft };
  const ok = edges.filter((e) => e.from >= 0 && e.to >= 0 && e.from !== e.to);
  const centre = (n) => ({ x: nodes[n].x + nodes[n].w / 2, y: nodes[n].y + nodes[n].h / 2 });

  // Pass 1
  let router = await newRouter(A, buffer, nudge);
  let shapes = nodes.map((b) => {
    const s = router.addShape({ x: b.x, y: b.y, width: b.w, height: b.h });
    // A diamond or circle tip takes one line while the node has up to 4, so lines leave by different tips.
    const deg = ok.filter((e) => nodes[e.from] === b || nodes[e.to] === b).length;
    for (const [side, [x, y]] of Object.entries(SIDES)) s.addPin({ classId: 1, x, y, directions: DIR[side] }).setExclusive(b.point && deg <= 4);
    return s;
  });
  let conns = ok.map((e) => router.addConnector({ shape: shapes[e.from], pin: 1 }, { shape: shapes[e.to], pin: 1 }));
  router.processTransaction();
  const groups = new Map(); // "node:side" -> ends
  ok.forEach((e, k) => {
    const r = conns[k].displayRoute();
    for (const [node, pt, other, end] of [[e.from, r[0], e.to, "src"], [e.to, r[r.length - 1], e.from, "dst"]]) {
      const side = sideOf(pt, nodes[node]), key = `${node}:${side}`;
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push({ k, end, node, side, toward: centre(other) });
    }
  });
  router.delete();

  // Pass 2
  const pinOf = new Map(); // `${k}:${end}` -> { node, classId }
  let nextId = 2;
  router = await newRouter(A, buffer, nudge);
  shapes = nodes.map((b) => router.addShape({ x: b.x, y: b.y, width: b.w, height: b.h }));
  for (const ends of groups.values()) {
    const { node, side } = ends[0], b = nodes[node], along = side === "top" || side === "bottom";
    // Order the ends along the side by the direction of the node they lead to (angle around this node's
    // centre), so lines leaving one side fan out without crossing each other.
    const c = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
    const ang = (en) => { const a = Math.atan2(en.toward.y - c.y, en.toward.x - c.x); return side === "left" && a < 0 ? a + 2 * Math.PI : a; };
    const desc = side === "bottom" || side === "left";
    ends.sort((p, q) => (desc ? ang(q) - ang(p) : ang(p) - ang(q)));
    const len = along ? b.w : b.h;
    const slots = b.point ? 1 : Math.max(1, Math.min(ends.length, Math.floor(len / minGap) - 1));
    const ids = [];
    for (let j = 0; j < slots; j++) {
      const f = (j + 1) / (slots + 1), [cx, cy] = SIDES[side], id = nextId++;
      shapes[node].addPin({ classId: id, x: along ? f : cx, y: along ? cy : f, directions: DIR[side] }).setExclusive(false);
      ids.push(id);
    }
    ends.forEach((en, j) => pinOf.set(`${en.k}:${en.end}`, { node, classId: ids[Math.floor((j * slots) / ends.length)] }));
  }
  conns = ok.map((e, k) => {
    const s = pinOf.get(`${k}:src`), d = pinOf.get(`${k}:dst`);
    return router.addConnector({ shape: shapes[s.node], pin: s.classId }, { shape: shapes[d.node], pin: d.classId });
  });
  router.processTransaction();
  const routes = ok.map((e, k) => {
    const pts = straighten(conns[k].displayRoute().map((p) => ({ x: p.x, y: p.y })));
    if (e.trim && pts.length > 1) {
      const a = pts[pts.length - 2], b = pts[pts.length - 1], l = Math.hypot(b.x - a.x, b.y - a.y);
      if (l > e.trim * 2) pts[pts.length - 1] = { x: b.x - ((b.x - a.x) / l) * e.trim, y: b.y - ((b.y - a.y) / l) * e.trim };
    }
    return { i: e.i, id: e.id, pts };
  });
  router.delete();
  return routes;
}

// Runs inside the page: draw the routes with rounded corners and move edge labels onto them.
export function applyRoutes(svg, routes, r) {
  const blocked = [...svg.querySelectorAll("g.node")].map((n) => { const b = n.getBoundingClientRect(); return { x: b.left, y: b.top, w: b.width, h: b.height }; });
  for (const { i, id, pts: screen } of routes) {
    const p = svg.querySelector(`path[data-pd-edge="${i}"]`);
    if (!p || screen.length < 2) continue;
    const inv = p.getScreenCTM().inverse();
    const pts = screen.map((q) => new DOMPoint(q.x, q.y).matrixTransform(inv))
      .filter((q, k, a) => k === 0 || Math.hypot(q.x - a[k - 1].x, q.y - a[k - 1].y) > 0.5);
    let d = `M${pts[0].x},${pts[0].y}`;
    for (let k = 1; k < pts.length - 1; k++) {
      const a = pts[k - 1], b = pts[k], c = pts[k + 1];
      const l1 = Math.hypot(b.x - a.x, b.y - a.y), l2 = Math.hypot(c.x - b.x, c.y - b.y), t = Math.min(r, l1 / 2, l2 / 2);
      d += ` L${b.x + ((a.x - b.x) / l1) * t},${b.y + ((a.y - b.y) / l1) * t} Q${b.x},${b.y} ${b.x + ((c.x - b.x) / l2) * t},${b.y + ((c.y - b.y) / l2) * t}`;
    }
    const z = pts[pts.length - 1];
    p.setAttribute("d", `${d} L${z.x},${z.y}`);
    // Label: on the longest free stretch of the route, clear of nodes and labels placed so far.
    const lab = id && svg.querySelector(`g.edgeLabel > g.label[data-id="${CSS.escape(id)}"]`);
    if (!lab || !lab.textContent.trim()) continue;
    const outer = lab.parentNode, m = outer.parentNode.getScreenCTM().inverse();
    const lr = lab.getBoundingClientRect(), w = lr.width, h = lr.height;
    const segs = screen.slice(1).map((b, k) => ({ a: screen[k], b, l: Math.hypot(b.x - screen[k].x, b.y - screen[k].y) })).sort((x, y) => y.l - x.l);
    const clash = (c) => {
      const r = { x: c.x - w / 2 - 3, y: c.y - h / 2 - 3, w: w + 6, h: h + 6 };
      return blocked.reduce((sum, o) => sum + Math.max(0, Math.min(r.x + r.w, o.x + o.w) - Math.max(r.x, o.x)) * Math.max(0, Math.min(r.y + r.h, o.y + o.h) - Math.max(r.y, o.y)), 0);
    };
    const fs = [0.5]; for (let f = 0.05; f < 0.5; f += 0.05) fs.push(0.5 - f, 0.5 + f);
    let spot = null, least = Infinity;
    for (const sg of segs) {
      for (const f of fs) {
        const c = { x: sg.a.x + (sg.b.x - sg.a.x) * f, y: sg.a.y + (sg.b.y - sg.a.y) * f }, v = clash(c);
        if (v < least) { least = v; spot = c; }
        if (v === 0) break;
      }
      if (least === 0) break;
    }
    const q = new DOMPoint(spot.x, spot.y).matrixTransform(m);
    outer.setAttribute("transform", `translate(${q.x}, ${q.y})`);
    lab.setAttribute("transform", "translate(0, 0)");
    const now = lab.getBoundingClientRect(), k = outer.getScreenCTM().a || 1;
    lab.setAttribute("transform", `translate(${(spot.x - (now.left + now.width / 2)) / k}, ${(spot.y - (now.top + now.height / 2)) / k})`);
    blocked.push({ x: spot.x - w / 2, y: spot.y - h / 2, w, h });
  }
}
