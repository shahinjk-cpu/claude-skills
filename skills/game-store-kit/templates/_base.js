// Shared look for every template so all assets share ONE visual system.
// Reads window.BRAND (store-assets/brand.json) and window.JOB (per-asset data).
(function () {
  const B = window.BRAND || {}, J = window.JOB || {};
  const C = Object.assign({ primary: '#6d28d9', secondary: '#db2777', accent: '#facc15', dark: '#0b0720', light: '#ffffff', text: '#ffffff' }, B.colors || {});
  const F = Object.assign({ display: 'Lilita One', body: 'Nunito' }, B.fonts || {});
  const S = Object.assign({ corner: 0.06, grain: 0.07, glow: true, upper: true, blurShot: true }, B.style || {});
  const W = J.w, H = J.h, P = H > W; // portrait?
  const root = document.documentElement.style;
  for (const [k, v] of Object.entries(C)) root.setProperty('--' + k, v);
  root.setProperty('--display', `'${F.display}', 'Arial Black', sans-serif`);
  root.setProperty('--body', `'${F.body}', 'Helvetica Neue', Arial, sans-serif`);
  root.setProperty('--stroke', S.textStroke || 'transparent'); root.setProperty('--stroke-w', S.textStroke ? (S.strokeWidth || 0.012) * Math.min(W, H) + 'px' : '0px');
  root.setProperty('--W', W + 'px'); root.setProperty('--H', H + 'px');

  // Fonts: local files (brand.fonts.displayFile/bodyFile) or Google Fonts by family name.
  const fontJobs = [];
  const face = (fam, url) => { const ff = new FontFace(fam, `url(${url})`); document.fonts.add(ff); fontJobs.push(ff.load().catch(() => {})); };
  if (F.displayFile) face(F.display, F.displayFile);
  if (F.bodyFile) face(F.body, F.bodyFile);
  const g = [F.displayFile ? null : F.display, F.bodyFile ? null : F.body].filter(Boolean);
  // Google Fonts: ask for heavy weights; families that only ship one weight (Lilita One, Luckiest Guy...) reject
  // a multi-weight request with HTTP 400, so fall back to the plain family request.
  const gfont = (fam) => new Promise(res => {
    const add = (href, onfail) => { const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = href; l.onload = () => res(true); l.onerror = onfail; document.head.appendChild(l); };
    const base = 'https://fonts.googleapis.com/css2?family=' + encodeURIComponent(fam);
    add(base + ':wght@400;700;800;900&display=block', () => add(base + '&display=block', () => res(false)));
    setTimeout(() => res(false), 8000);
  }).then(() => document.fonts.load(`900 64px '${fam}'`).catch(() => {}));
  for (const fam of new Set(g)) fontJobs.push(gfont(fam));
  window.READY = Promise.all(fontJobs).then(() => document.fonts.ready).then(() => window.LAYOUT && window.LAYOUT());

  const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
  const esc = s => String(s ?? '').replace(/[&<>]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[c]));
  // "*word*" -> accent highlight, "\n" -> line break
  // never break inside hyphenated words ("T-Rex") or between a highlighted word and its punctuation
  const rich = s => esc(s).replace(/(\S*\w-\w\S*)/g, '<span style="white-space:nowrap">$1</span>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>').replace(/\\n|\n/g, '<br>');

  // Background shared by all assets. index shifts blobs so a screenshot SET reads as one panorama.
  function background(host, opts = {}) {
    const i = J.index || 0;
    const bg = el('div', 'bg');
    bg.appendChild(el('div', 'bg-base'));
    if (S.blurShot && (opts.shot || J.image)) { const b = el('img', 'bg-shot'); b.src = opts.shot || J.image; bg.appendChild(b); }
    const blobs = el('div', 'bg-blobs');
    const span = (J.total || 6) + 1;
    for (let k = 0; k < span * 2; k++) {
      const d = el('div', 'blob');
      const size = (P ? H : W) * (0.55 + ((k * 37) % 5) * 0.09);
      const x = (k * 0.62 - i) * W + W * 0.2;
      const y = H * (0.15 + ((k * 53) % 7) / 9);
      d.style.cssText = `width:${size}px;height:${size}px;left:${x - size / 2}px;top:${y - size / 2}px;background:radial-gradient(circle, ${k % 3 === 0 ? 'var(--secondary)' : k % 3 === 1 ? 'var(--primary)' : 'var(--accent)'} 0%, transparent 65%);opacity:${k % 3 === 2 ? 0.28 : 0.55}`;
      blobs.appendChild(d);
    }
    bg.appendChild(blobs);
    // diagonal light rays
    const rays = el('div', 'rays'); bg.appendChild(rays);
    // optional sunburst (style.burst) so backgrounds echo a sunburst icon; burstAt = focal point
    if (S.burst) {
      const at = opts.burstAt || J.burstAt || (P ? '50% 14%' : '30% 50%');
      const b = el('div', 'burst');
      b.style.background = `radial-gradient(circle at ${at}, color-mix(in oklab, var(--accent) ${Math.round((S.burst.glow ?? .55) * 100)}%, transparent) 0%, transparent ${P ? 38 : 45}%), repeating-conic-gradient(from 0deg at ${at}, rgba(255,255,255,${S.burst.opacity ?? .09}) 0deg 7deg, transparent 7deg 18deg)`;
      b.style.maskImage = b.style.webkitMaskImage = `radial-gradient(circle at ${at}, #000 0%, transparent ${P ? 70 : 75}%)`;
      bg.appendChild(b);
    }
    const grain = el('div', 'grain'); grain.style.opacity = S.grain; bg.appendChild(grain);
    bg.appendChild(el('div', 'vignette'));
    host.appendChild(bg);
  }

  function decor(host) {
    for (let d of J.decor || []) {
      if (!P && d.land) d = { ...d, ...d.land }; // optional landscape override {x,y,size,rot}
      const im = el('img', 'decor'); im.src = d.src;
      im.style.cssText = `left:${d.x}%;top:${d.y}%;width:${(d.size || 18) / 100 * Math.min(W, H)}px;transform:translate(-50%,-50%) rotate(${d.rot || 0}deg);${d.blur ? `filter:blur(${d.blur}px) drop-shadow(0 30px 40px rgba(0,0,0,.45))` : ''}`;
      host.appendChild(im);
    }
  }

  function fit(node, maxPx, minPx) { // biggest font size whose text box fits the allowed width/height
    const limit = parseFloat(node.style.maxHeight) || node.parentElement.clientHeight;
    node.style.maxHeight = 'none'; node.style.overflow = 'visible';
    const tooBig = () => {
      return node.offsetHeight > limit + 1 || node.scrollWidth > node.clientWidth + node.clientWidth * 0.01;
    };
    let s = maxPx; node.style.fontSize = s + 'px';
    while (s > minPx && tooBig()) { s -= 2; node.style.fontSize = s + 'px'; }
    return s;
  }

  // ---------------------------------------------------------------- premium building blocks
  // seeded random so every render of the same shot is identical
  const rng = seed => () => { seed |= 0; seed = seed + 0x6D2B79F5 | 0; let t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };

  // Modern flagship phone (iPhone-18-like proportions: ~19.5:9 screen, ultra-thin bezel, pill cutout,
  // flat titanium band, side buttons). No logos/branding. Returns {el, w, h, screen}.
  // opts: { img, screenW, aspect (screen w/h), landscape, finish: 'black'|'silver'|'desert'|'brand', crop }
  function phone(opts) {
    const land = !!opts.landscape;
    const aspect = opts.aspect || (land ? 2622 / 1206 : 1206 / 2622);
    const sw = opts.screenW, sh = sw / aspect;            // screen size
    const short = Math.min(sw, sh);
    const bez = short * 0.028, band = short * 0.016;       // black bezel + metal band
    const w = sw + 2 * (bez + band), h = sh + 2 * (bez + band);
    const rOuter = Math.min(w, h) * 0.165, rScreen = rOuter - bez - band * .6;
    const finishes = {
      black: ['#4a4c52', '#1b1c20', '#5d6067', '#141518'], silver: ['#f1f2f4', '#b9bcc2', '#ffffff', '#9da1a8'],
      desert: ['#d8c3a8', '#9c8467', '#efe0cc', '#86705a'],
      brand: ['color-mix(in oklab, var(--primary) 55%, #fff)', 'color-mix(in oklab, var(--primary) 70%, #000)', 'color-mix(in oklab, var(--primary) 30%, #fff)', 'color-mix(in oklab, var(--primary) 60%, #000)'],
    };
    const f = finishes[opts.finish || S.deviceFinish || 'black'] || finishes.black;
    const ph = el('div', 'phone');
    ph.style.cssText = `width:${w}px;height:${h}px;border-radius:${rOuter}px;padding:${band}px;background:linear-gradient(${land ? 180 : 90}deg, ${f[0]} 0%, ${f[1]} 12%, ${f[2]} 50%, ${f[1]} 88%, ${f[3]} 100%);`;
    // side buttons
    const btn = (side, at, len) => {
      const b = el('div', 'pbtn'); const t = short * 0.012;
      const along = land ? 'left' : 'top', across = land ? (side === 'a' ? 'top' : 'bottom') : (side === 'a' ? 'left' : 'right');
      b.style.cssText = `${along}:${at * (land ? w : h)}px;${across}:${-t * .7}px;${land ? 'width' : 'height'}:${len * (land ? w : h)}px;${land ? 'height' : 'width'}:${t}px;border-radius:${t}px;background:linear-gradient(${land ? 180 : 90}deg, ${f[1]}, ${f[2]}, ${f[1]});`;
      ph.appendChild(b);
    };
    btn('a', .17, .035); btn('a', .235, .06); btn('a', .31, .06); btn('b', .27, .09); btn('b', .6, .05);
    const bezel = el('div', 'pbezel'); bezel.style.cssText = `border-radius:${rOuter - band}px;padding:${bez}px;`;
    const screen = el('div', 'pscreen'); screen.style.cssText = `width:${sw}px;height:${sh}px;border-radius:${rScreen}px;`;
    const img = el('img'); img.src = opts.img; if (opts.crop) img.style.objectPosition = opts.crop; screen.appendChild(img);
    const isl = el('div', 'pisland');
    const iw = short * 0.27, ih = short * 0.078;
    isl.style.cssText = land ? `left:${short * 0.03}px;top:${(sh - iw) / 2}px;width:${ih}px;height:${iw}px;border-radius:${ih}px;`
                             : `top:${short * 0.03}px;left:${(sw - iw) / 2}px;width:${iw}px;height:${ih}px;border-radius:${ih}px;`;
    screen.appendChild(isl);
    screen.appendChild(el('div', 'pglare'));
    bezel.appendChild(screen); ph.appendChild(bezel);
    return { el: ph, w, h, screen: { w: sw, h: sh, x: band + bez, y: band + bez } };
  }

  // Glass feature chips: [{text, icon}] or ["text"]
  function chips(list, size) {
    const row = el('div', 'chips');
    for (const c of list || []) {
      const it = typeof c === 'string' ? { text: c } : c;
      const ch = el('div', 'chip'); ch.style.fontSize = size + 'px';
      if (it.icon) { const i = el('img'); i.src = it.icon; ch.appendChild(i); }
      ch.appendChild(el('span', null, rich(it.text))); row.appendChild(ch);
    }
    return row;
  }

  // Zoom bubble on a detail of the frame. c = { fx, fy (focus 0-1 in frame), zoom, x, y (% canvas), size (% short side), label }
  function callout(c, frameSrc, frameAspect) {
    // zoom = how many bubble-widths the whole frame spans (3 => the bubble shows a third of the frame's width)
    const D = (c.size || 30) / 100 * Math.min(W, H), Z = c.zoom || 3;
    const bgW = D * Z, bgH = bgW / frameAspect;
    const b = el('div', 'callout');
    b.style.cssText = `width:${D}px;height:${D}px;left:${c.x}%;top:${c.y}%;background-image:url("${frameSrc}");background-size:${bgW}px ${bgH}px;background-position:${D / 2 - c.fx * bgW}px ${D / 2 - c.fy * bgH}px;border-width:${D * .035}px;`;
    if (c.label) { const l = el('div', 'clabel', rich(c.label)); l.style.fontSize = D * .11 + 'px'; b.appendChild(l); }
    return b;
  }

  // Floating game objects at different depths. items: [src], count, avoid: [{x,y,w,h}] in px
  function floaters(host, items, count, seed, slots) {
    if (!items || !items.length || !count) return;
    const r = rng(seed * 7919 + 13);
    let near = 0; const pick = [...slots].sort(() => r() - .5).filter(s => s.depth !== 'near' || near++ < 1 && r() < .5).slice(0, count);
    pick.forEach((s, k) => {
      const im = el('img', 'floater'); im.src = items[(seed * 3 + k * 2) % items.length];
      const size = s.size * Math.min(W, H), rot = (r() - .5) * 50;
      const blur = s.depth === 'near' ? Math.min(W, H) * 0.004 : s.depth === 'far' ? Math.min(W, H) * 0.0025 : 0;
      im.style.cssText = `left:${s.x}%;top:${s.y}%;width:${size}px;transform:translate(-50%,-50%) rotate(${rot}deg);z-index:${s.depth === 'near' ? 7 : s.depth === 'far' ? 1 : 6};` +
        `filter:${blur ? `blur(${blur}px) ` : ''}drop-shadow(0 ${size * .12}px ${size * .14}px rgba(0,0,0,.4));opacity:${s.depth === 'far' ? .75 : 1}`;
      host.appendChild(im);
    });
  }

  // Object straddling the edge between consecutive screenshots (half here, half on the neighbour)
  function bridge(host, b, side) {
    if (!b) return;
    const im = el('img', 'floater'); im.src = b.src; const size = (b.size || 22) / 100 * Math.min(W, H);
    im.style.cssText = `left:${side === 'right' ? W : 0}px;top:${b.y}%;width:${size}px;transform:translate(-50%,-50%) rotate(${b.rot || 0}deg);z-index:6;filter:drop-shadow(0 ${size * .1}px ${size * .12}px rgba(0,0,0,.4));`;
    host.appendChild(im);
  }

  // Soft bokeh / sparkles for depth
  function bokeh(host, n, seed) {
    const r = rng(seed * 31 + 7), layer = el('div', 'bokeh');
    for (let k = 0; k < n; k++) {
      const d = el('div'), s = Math.min(W, H) * (0.006 + r() * 0.02);
      d.style.cssText = `left:${r() * 100}%;top:${r() * 100}%;width:${s}px;height:${s}px;opacity:${.25 + r() * .5};filter:blur(${r() < .4 ? s * .4 : 0}px)`;
      layer.appendChild(d);
    }
    host.appendChild(layer);
  }

  window.KIT = { B, J, C, F, S, W, H, P, el, esc, rich, background, decor, fit, phone, chips, callout, floaters, bridge, bokeh, rng };
})();
