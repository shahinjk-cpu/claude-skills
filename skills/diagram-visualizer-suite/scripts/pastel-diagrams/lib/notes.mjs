// Sticky notes and stickers, written as Mermaid comments so Mermaid ignores them:
//   %% note api: Rate limit is 100 requests a minute | Mustafa | green
//   %% sticker api: +1
//   %% sticker db: 🎉 | bottom-left
//   %% sticker web: WIP | top-left | orange
// Notes sit next to their card in free space; stickers pin to a card corner.
// Emoji are drawn from Twemoji (graphics CC-BY 4.0) so they look the same everywhere.
import fs from "node:fs";
import path from "node:path";
import { pkgDir } from "./style.mjs";

const NOTE = /^\s*%%\s*note\s+([\w-]+)\s*:\s*(.+)$/gm;
const STICKER = /^\s*%%\s*sticker\s+([\w-]+)\s*:\s*(.+)$/gm;
const CORNER = /^(top|bottom)-(left|right)$/;

// Twemoji file name: code points in hex, without U+FE0F unless the emoji is a ZWJ sequence.
function twemoji(text) {
  let cps = [...text].map((c) => c.codePointAt(0));
  if (!cps.includes(0x200d)) cps = cps.filter((c) => c !== 0xfe0f);
  const f = path.join(pkgDir("@twemoji/svg"), `${cps.map((c) => c.toString(16)).join("-")}.svg`);
  return fs.existsSync(f) ? `data:image/svg+xml;base64,${fs.readFileSync(f).toString("base64")}` : null;
}

export function parseNotes(code) {
  const split = (s) => s.split("|").map((p) => p.trim());
  const notes = [...code.matchAll(NOTE)].map(([, id, rest]) => {
    const [text, author = "", colour = "yellow"] = split(rest);
    return { kind: "note", id, text, author, colour };
  });
  const stickers = [...code.matchAll(STICKER)].map(([, id, rest]) => {
    const [text, ...opts] = split(rest);
    const corner = opts.find((o) => CORNER.test(o)) || "top-right";
    const colour = opts.find((o) => o && !CORNER.test(o)) || "purple";
    return { kind: "sticker", id, text, corner, colour, src: twemoji(text) };
  });
  return [...notes, ...stickers];
}

// Runs in the page.
export function applyNotes(svg, items, font) {
  const NS = "http://www.w3.org/2000/svg", XH = "http://www.w3.org/1999/xhtml";
  const COLOURS = { yellow: "#FFF1A8", green: "#BDEFB8", pink: "#FFD1E1", blue: "#CFE4FF", purple: "#E4D8FF", orange: "#FFDDB8" };
  const mk = (tag, attrs = {}, parent) => {
    const e = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v);
    if (parent) parent.appendChild(e);
    return e;
  };
  const inv = svg.getScreenCTM().inverse();
  const local = (r) => {
    const p = new DOMPoint(r.left, r.top).matrixTransform(inv), q = new DOMPoint(r.right, r.bottom).matrixTransform(inv);
    return { x: p.x, y: p.y, w: q.x - p.x, h: q.y - p.y };
  };
  const nodeOf = (id) => [...svg.querySelectorAll("g.node")].find((g) => new RegExp(`-${id}-\\d+$`).test(g.id) || g.id.endsWith(`-${id}`));

  // Shared filters: a soft shadow for notes, a white die-cut edge plus shadow for stickers.
  const defs = mk("defs", {}, svg);
  defs.innerHTML = `
    <filter id="pd-note-shadow" x="-20%" y="-20%" width="140%" height="150%"><feDropShadow dx="0" dy="3" stdDeviation="4" flood-color="#0F172A" flood-opacity=".14"/></filter>
    <filter id="pd-sticker" x="-40%" y="-40%" width="180%" height="180%">
      <feMorphology in="SourceAlpha" operator="dilate" radius="3.5" result="grow"/>
      <feFlood flood-color="#FFFFFF"/><feComposite in2="grow" operator="in" result="edge"/>
      <feDropShadow in="edge" dx="0" dy="1.5" stdDeviation="1.6" flood-color="#0F172A" flood-opacity=".28" result="edgeShadow"/>
      <feMerge><feMergeNode in="edgeShadow"/><feMergeNode in="SourceGraphic"/></feMerge>
    </filter>`;
  const layer = mk("g", { class: "pd-notes" }, svg), missing = [];

  // Space already taken: cards, group captions, edge labels and edge paths (sampled).
  const blocked = [...svg.querySelectorAll("g.node, g.cluster-label, g.edgeLabel")].map((e) => local(e.getBoundingClientRect()));
  for (const p of svg.querySelectorAll("path.flowchart-link, path.transition")) {
    const len = p.getTotalLength(), m = p.getScreenCTM();
    for (let s = 0; s <= len; s += 8) {
      const pt = p.getPointAtLength(s), sp = new DOMPoint(pt.x, pt.y).matrixTransform(m);
      const lp = sp.matrixTransform(inv);
      blocked.push({ x: lp.x - 2, y: lp.y - 2, w: 4, h: 4 });
    }
  }
  const hits = (a) => blocked.reduce((n, b) => n + Math.max(0, Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x)) * Math.max(0, Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y)), 0);

  // Cluster borders count as taken too, so a note never straddles a group panel's edge.
  for (const r of svg.querySelectorAll("g.cluster > rect")) {
    const b = local(r.getBoundingClientRect());
    blocked.push({ x: b.x, y: b.y - 3, w: b.w, h: 6 }, { x: b.x, y: b.y + b.h - 3, w: b.w, h: 6 },
                 { x: b.x - 3, y: b.y, w: 6, h: b.h }, { x: b.x + b.w - 3, y: b.y, w: 6, h: b.h });
  }
  const pad = (a, p) => ({ x: a.x - p, y: a.y - p, w: a.w + 2 * p, h: a.h + 2 * p });

  for (const it of items.filter((i) => i.kind === "note")) {
    const g = nodeOf(it.id);
    if (!g) { missing.push(it.id); continue; }
    const n = local(g.getBoundingClientRect()), W = 168;
    // Build the note first so its height can follow the text.
    const box = mk("g", { class: "pd-note" }, layer);
    const rect = mk("rect", { width: W, rx: 2, fill: COLOURS[it.colour] || it.colour, filter: "url(#pd-note-shadow)" }, box);
    const fo = mk("foreignObject", { x: 14, y: 12, width: W - 28, height: 400 }, box);
    const div = document.createElementNS(XH, "div");
    div.setAttribute("style", `font-family:${font};color:#1F2937`);
    div.innerHTML = `<div style="font-size:13px;line-height:1.4"></div><div style="font-size:11px;color:#4B5563;margin-top:14px"></div>`;
    div.children[0].textContent = it.text;
    div.children[1].textContent = it.author;
    if (!it.author) div.children[1].remove();
    fo.appendChild(div);
    const H = Math.max(84, Math.ceil(div.getBoundingClientRect().height / svg.getScreenCTM().a) + 26);
    fo.setAttribute("height", H - 24);
    rect.setAttribute("height", H);
    // Nearest spot with nothing under it (cards, lines, labels, panel edges), searched around the card.
    const cx = n.x + n.w / 2, cy = n.y + n.h / 2, gap = 18;
    let best = null, cost = Infinity;
    for (let dx = -360; dx <= 360; dx += 12) for (let dy = -300; dy <= 300; dy += 12) {
      const a = { x: cx + dx - W / 2, y: cy + dy - H / 2, w: W, h: H };
      const ox = Math.max(0, n.x - (a.x + a.w), a.x - (n.x + n.w)), oy = Math.max(0, n.y - (a.y + a.h), a.y - (n.y + n.h));
      if (Math.max(ox, oy) < gap) continue;
      const c = hits(pad(a, 8)) * 1e4 + Math.hypot(a.x + W / 2 - cx, a.y + H / 2 - cy); // closest to the card centre
      if (c < cost) { cost = c; best = a; }
    }
    box.setAttribute("transform", `translate(${best.x}, ${best.y})`);
    blocked.push(best);
  }

  const INK = { purple: "#9747FF", green: "#14AE5C", pink: "#E5397F", blue: "#0D99FF", orange: "#F2780C", red: "#E5383B", yellow: "#E8A600" };
  for (const it of items.filter((i) => i.kind === "sticker")) {
    const g = nodeOf(it.id);
    if (!g) { missing.push(it.id); continue; }
    const n = local(g.getBoundingClientRect());
    const [, v, h] = it.corner.match(/^(top|bottom)-(left|right)$/);
    const x = h === "left" ? n.x + 4 : n.x + n.w - 4, y = v === "bottom" ? n.y + n.h - 2 : n.y + 2;
    // A fixed tilt per sticker, so renders are repeatable.
    const tilt = ([...(it.text + it.id)].reduce((a, c) => a + c.codePointAt(0), 0) % 19) - 9;
    const s = mk("g", { class: "pd-sticker", transform: `translate(${x}, ${y}) rotate(${tilt})`, filter: "url(#pd-sticker)" }, layer);
    if (it.src) {
      mk("image", { href: it.src, x: -16, y: -16, width: 32, height: 32 }, s);
    } else {
      const t = mk("text", {
        "text-anchor": "middle", "dominant-baseline": "central",
        style: `font-family:${font};font-size:24px;font-weight:800;fill:${INK[it.colour] || it.colour};letter-spacing:-.03em`,
      }, s);
      t.textContent = it.text;
    }
  }
  return missing;
}
