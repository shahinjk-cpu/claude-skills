// Scene toolkit for designed key art (splash screens, posters). Load after _base.js.
// Everything is in % of the canvas or fractions of the short side, so ONE scene renders well at
// 1080x1920, 1920x1080 and 2732x2732. Layers are appended in call order (back to front).
(function () {
  const { W, H, P, el, rng } = KIT;
  const short = Math.min(W, H);
  const NS = 'http://www.w3.org/2000/svg';
  let z = 0;
  const layer = (cls = '') => { const d = el('div', 'sc-layer ' + cls); d.style.cssText = `position:absolute;inset:0;z-index:${++z};pointer-events:none;`; document.body.appendChild(d); return d; };
  const svgLayer = () => { const d = layer(); const s = document.createElementNS(NS, 'svg'); s.setAttribute('viewBox', `0 0 ${W} ${H}`); s.setAttribute('width', W); s.setAttribute('height', H); s.style.cssText = 'position:absolute;inset:0;overflow:visible'; d.appendChild(s); return s; };
  const svgEl = (tag, attrs, parent) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); parent && parent.appendChild(e); return e; };
  const px = (x, y) => [x / 100 * W, y / 100 * H];

  // vertical sky gradient: stops = [[0,'#123'],[0.6,'#f80'],[1,'#ff0']]
  function sky(stops, angle = 180) { const d = layer(); d.style.background = `linear-gradient(${angle}deg, ${stops.map(([o, c]) => `${c} ${o * 100}%`).join(',')})`; return d; }

  // soft radial light
  function glow(x, y, r, color, opacity = 1, blend = 'screen') {
    const d = layer(); const [cx, cy] = px(x, y); const R = r * short;
    d.style.background = `radial-gradient(circle at ${cx}px ${cy}px, ${color} 0px, transparent ${R}px)`; d.style.opacity = opacity; d.style.mixBlendMode = blend; return d;
  }

  // light rays from a point
  function rays(x, y, { count = 18, opacity = .12, color = '#fff', spread = 360, from = 0, fade = .8 } = {}) {
    const d = layer(); const [cx, cy] = px(x, y); const step = spread / count;
    d.style.background = `repeating-conic-gradient(from ${from}deg at ${cx}px ${cy}px, color-mix(in oklab, ${color} ${opacity * 100}%, transparent) 0deg ${step * .38}deg, transparent ${step * .38}deg ${step}deg)`;
    d.style.maskImage = d.style.webkitMaskImage = `radial-gradient(circle at ${cx}px ${cy}px, #000 0%, transparent ${fade * Math.hypot(W, H) / 2}px)`;
    d.style.mixBlendMode = 'screen'; return d;
  }

  // procedural silhouette band. y = baseline (% H), amp = height (frac H)
  // kind: 'hills' | 'mountains' | 'volcano' | 'dunes' ; trees: 'palm' | 'pine' | 'round' | null
  function ridge({ y = 75, amp = .12, color = '#123', seed = 1, kind = 'hills', trees = null, treeEvery = .12, treeSize = .12, blur = 0, glowColor = null, highlight = null } = {}) {
    const s = svgLayer(); const r = rng(seed * 131 + 17); const base = y / 100 * H, A = amp * H;
    const N = kind === 'mountains' ? 9 : kind === 'dunes' ? 4 : 6;
    const pts = []; for (let i = 0; i <= N; i++) pts.push([i / N * W, base - A * (kind === 'mountains' ? (.35 + r() * .65) : (.3 + r() * .7))]);
    let d = `M${-W * .1} ${H + 10} L${-W * .1} ${pts[0][1]}`;
    if (kind === 'mountains') pts.forEach(([x, yy], i) => { d += ` L${x} ${yy}`; if (i < N) d += ` L${x + W / N / 2} ${base - A * (.1 + r() * .3)}`; });
    else for (let i = 0; i < N; i++) { const [x1, y1] = pts[i], [x2, y2] = pts[i + 1]; d += ` C${x1 + W / N * .5} ${y1} ${x2 - W / N * .5} ${y2} ${x2} ${y2}`; }
    d += ` L${W * 1.1} ${pts[N][1]} L${W * 1.1} ${H + 10} Z`;
    const g = svgEl('g', blur ? { filter: `blur(${blur * short}px)` } : {}, s);
    if (glowColor) svgEl('path', { d, fill: 'none', stroke: glowColor, 'stroke-width': short * .012, opacity: .55, filter: `blur(${short * .01}px)` }, g);
    svgEl('path', { d, fill: color }, g);
    if (highlight) svgEl('path', { d, fill: 'none', stroke: highlight, 'stroke-width': short * .004, opacity: .5 }, g);
    if (kind === 'volcano') { // crater + lava glow on the highest point
      const top = pts.reduce((a, b) => (b[1] < a[1] ? b : a));
      const cw = short * .08; svgEl('path', { d: `M${top[0] - cw * 1.8} ${top[1] + A * .25} L${top[0] - cw * .6} ${top[1] - A * .12} L${top[0] + cw * .6} ${top[1] - A * .12} L${top[0] + cw * 1.8} ${top[1] + A * .25} Z`, fill: color }, g);
      svgEl('ellipse', { cx: top[0], cy: top[1] - A * .12, rx: cw * .7, ry: cw * .18, fill: '#ffb347', filter: `blur(${short * .006}px)` }, g);
      ridge.lastVolcano = { x: top[0] / W * 100, y: (top[1] - A * .12) / H * 100 };
    }
    if (trees) {
      const sampleY = x => { // y on the curve (approx, linear between points)
        const t = x / W * N, i = Math.min(N - 1, Math.max(0, Math.floor(t))), f = t - i; return pts[i][1] * (1 - f) + pts[i + 1][1] * f; };
      for (let x = r() * W * treeEvery; x < W; x += W * treeEvery * (.6 + r() * .8)) tree(g, trees, x, sampleY(x) + A * .08, treeSize * short * (.7 + r() * .6), color, r);
    }
    return s;
  }
  function tree(g, kind, x, y, h, color, r) {
    if (kind === 'pine') { for (let k = 0; k < 3; k++) { const w = h * (.42 - k * .1), ty = y - h * (.25 + k * .25); svgEl('path', { d: `M${x - w} ${ty + h * .3} L${x} ${ty - h * .1} L${x + w} ${ty + h * .3} Z`, fill: color }, g); } svgEl('rect', { x: x - h * .03, y: y - h * .2, width: h * .06, height: h * .25, fill: color }, g); return; }
    if (kind === 'round') { svgEl('rect', { x: x - h * .04, y: y - h * .5, width: h * .08, height: h * .55, fill: color }, g); svgEl('circle', { cx: x, cy: y - h * .62, r: h * .3, fill: color }, g); svgEl('circle', { cx: x - h * .2, cy: y - h * .5, r: h * .2, fill: color }, g); svgEl('circle', { cx: x + h * .2, cy: y - h * .52, r: h * .22, fill: color }, g); return; }
    // palm: curved trunk + fronds
    const lean = (r() - .5) * h * .5, tx = x + lean, ty = y - h;
    svgEl('path', { d: `M${x - h * .035} ${y} Q${x + lean * .2} ${y - h * .5} ${tx - h * .02} ${ty} L${tx + h * .02} ${ty} Q${x + lean * .2 + h * .05} ${y - h * .5} ${x + h * .035} ${y} Z`, fill: color }, g);
    for (let k = 0; k < 6; k++) {
      const a = -Math.PI / 2 + (k - 2.5) * .55 + (r() - .5) * .2, L = h * (.42 + r() * .12);
      const ex = tx + Math.cos(a) * L, ey = ty + Math.sin(a) * L * .55 + L * .25;
      svgEl('path', { d: `M${tx} ${ty} Q${tx + Math.cos(a) * L * .5} ${ty + Math.sin(a) * L * .6 - L * .15} ${ex} ${ey} Q${tx + Math.cos(a) * L * .45} ${ty + Math.sin(a) * L * .45} ${tx} ${ty + h * .03} Z`, fill: color }, g);
    }
  }

  // comet / meteor streak from (x1,y1) to head (x2,y2); head: sprite url or null
  function comet(x1, y1, x2, y2, { width = .05, colors = ['#ff3d00', '#ffb347', '#fff6c9'], head = null, headSize = .16, glowSize = .35 } = {}) {
    const s = svgLayer(); const [ax, ay] = px(x1, y1), [bx, by] = px(x2, y2); const id = 'cg' + (++z);
    const lg = svgEl('linearGradient', { id, x1: ax, y1: ay, x2: bx, y2: by, gradientUnits: 'userSpaceOnUse' }, svgEl('defs', {}, s));
    svgEl('stop', { offset: 0, 'stop-color': colors[0], 'stop-opacity': 0 }, lg); svgEl('stop', { offset: .65, 'stop-color': colors[1], 'stop-opacity': .85 }, lg); svgEl('stop', { offset: 1, 'stop-color': colors[2], 'stop-opacity': 1 }, lg);
    const ang = Math.atan2(by - ay, bx - ax), wpx = width * short, nx = -Math.sin(ang), ny = Math.cos(ang);
    svgEl('path', { d: `M${ax} ${ay} L${bx + nx * wpx} ${by + ny * wpx} L${bx - nx * wpx} ${by - ny * wpx} Z`, fill: `url(#${id})`, filter: `blur(${short * .004}px)` }, s);
    svgEl('path', { d: `M${ax} ${ay} L${bx + nx * wpx * .35} ${by + ny * wpx * .35} L${bx - nx * wpx * .35} ${by - ny * wpx * .35} Z`, fill: colors[2], opacity: .7 }, s);
    glow(x2, y2, glowSize, colors[1], .9);
    if (head) sprite(head, x2, y2, headSize, { rot: ang * 180 / Math.PI - 45 });
    return s;
  }

  // sprite placement: x,y = centre in %, size = width as fraction of short side
  function sprite(src, x, y, size, { rot = 0, flip = false, shadow = true, glowColor = null, blur = 0, opacity = 1, filter = '' } = {}) {
    const d = layer(); const im = el('img'); im.src = src; const [cx, cy] = px(x, y); const w = size * short;
    im.style.cssText = `position:absolute;left:${cx}px;top:${cy}px;width:${w}px;transform:translate(-50%,-50%) rotate(${rot}deg) scaleX(${flip ? -1 : 1});opacity:${opacity};` +
      `filter:${filter} ${blur ? `blur(${blur * short}px) ` : ''}${shadow ? `drop-shadow(0 ${w * .06}px ${w * .08}px rgba(0,0,0,.45)) ` : ''}${glowColor ? `drop-shadow(0 0 ${w * .08}px ${glowColor})` : ''};`;
    d.appendChild(im); return im;
  }

  // speed lines behind a moving subject (angle in deg, direction of motion)
  function speed(x, y, { count = 7, len = .35, angle = 180, spread = .12, color = 'rgba(255,255,255,.75)', width = .008, seed = 3 } = {}) {
    const s = svgLayer(); const r = rng(seed); const [cx, cy] = px(x, y); const a = (angle + 180) * Math.PI / 180;
    for (let i = 0; i < count; i++) {
      const off = (r() - .5) * spread * short, L = len * short * (.5 + r() * .7), st = short * (.04 + r() * .08);
      const ox = cx - Math.sin(a) * off + Math.cos(a) * st, oy = cy + Math.cos(a) * off + Math.sin(a) * st;
      svgEl('line', { x1: ox, y1: oy, x2: ox + Math.cos(a) * L, y2: oy + Math.sin(a) * L, stroke: color, 'stroke-width': width * short * (.5 + r()), 'stroke-linecap': 'round', opacity: .4 + r() * .6 }, s);
    }
    return s;
  }

  // particles: 'embers' | 'sparkles' | 'snow' | 'leaves' | 'fireflies'
  function particles(kind, n = 60, { color = '#ffb347', seed = 9, area = [0, 0, 100, 100], size = 1 } = {}) {
    const d = layer(); const r = rng(seed);
    for (let i = 0; i < n; i++) {
      const p = el('div'); const s = short * (kind === 'snow' ? .006 : kind === 'leaves' ? .02 : .004) * (.5 + r() * 1.2) * size;
      const x = area[0] + r() * (area[2] - area[0]), y = area[1] + r() * (area[3] - area[1]);
      const shape = kind === 'leaves' ? 'border-radius:50% 0;' : kind === 'sparkles' ? 'clip-path:polygon(50% 0,60% 40%,100% 50%,60% 60%,50% 100%,40% 60%,0 50%,40% 40%);' : 'border-radius:50%;';
      p.style.cssText = `position:absolute;left:${x}%;top:${y}%;width:${s}px;height:${s * (kind === 'leaves' ? .55 : 1)}px;${shape}background:${color};opacity:${.35 + r() * .65};transform:rotate(${r() * 360}deg);` +
        (kind === 'embers' || kind === 'fireflies' || kind === 'sparkles' ? `box-shadow:0 0 ${s * 2.5}px ${color};` : '');
      d.appendChild(p);
    }
    return d;
  }

  function grain(opacity = .06) { const d = layer('grain'); d.style.opacity = opacity; return d; }
  function vignette(strength = .45) { const d = layer(); d.style.background = `radial-gradient(ellipse at 50% 45%, transparent 50%, rgba(0,0,0,${strength}) 100%)`; return d; }

  window.SCENE = { sky, glow, rays, ridge, comet, sprite, speed, particles, grain, vignette, layer, px, short };
})();
