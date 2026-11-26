// Theme loading and WCAG contrast checks.
// A theme is a JSON file in themes/ (see themes/pastel.json for every field).
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

export const THEMES_DIR = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../themes");
export const CARD_CLASSES = ["lav", "mint", "sky", "peach", "yellow", "grey", "decision", "ext"];

export function listThemes() {
  return fs.readdirSync(THEMES_DIR).filter((f) => f.endsWith(".json")).map((f) => f.slice(0, -5)).sort();
}

// name ("pastel"), name + dark ("pastel" + --dark -> pastel-dark), or a path to a .json file.
export function resolveTheme(nameOrPath = "pastel", dark = false) {
  const isPath = /[\\/]|\.json$/i.test(nameOrPath);
  let file = isPath ? path.resolve(nameOrPath) : path.join(THEMES_DIR, `${nameOrPath}.json`);
  if (dark && !/-dark\.json$/i.test(file)) file = file.replace(/\.json$/i, "-dark.json");
  if (!fs.existsSync(file)) {
    const hint = isPath ? "" : ` Built-in themes: ${listThemes().join(", ")}`;
    throw new Error(`Theme not found: ${file}.${hint}`);
  }
  return file;
}

export function loadTheme(file) {
  const t = JSON.parse(fs.readFileSync(file, "utf8"));
  const missing = ["canvas", "text", "muted", "line", "edgeText", "icon", "cluster", "note", "classes"].filter((k) => !(k in t));
  missing.push(...CARD_CLASSES.filter((c) => !t.classes?.[c]).map((c) => `classes.${c}`));
  if (missing.length) throw new Error(`Theme ${file} is missing: ${missing.join(", ")}`);
  return {
    font: "Inter", radius: { node: 14, cluster: 18, actor: 12 }, strokeWidth: 1, lineWidth: 1.4,
    page: t.canvas, pageCard: t.canvas, pageBorder: t.cluster.stroke, lifeline: t.cluster.stroke,
    ...t, file, dark: !!t.dark,
  };
}

// The light/dark partner of a theme file, or null.
export function partnerTheme(file) {
  const other = /-dark\.json$/i.test(file) ? file.replace(/-dark\.json$/i, ".json") : file.replace(/\.json$/i, "-dark.json");
  return fs.existsSync(other) ? other : null;
}

// ---------- WCAG 2.x contrast
function lum(hex) {
  const h = hex.replace("#", "");
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6);
  const [r, g, b] = [0, 2, 4].map((i) => parseInt(n.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
export function contrast(a, b) {
  const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p);
  return (x + 0.05) / (y + 0.05);
}

// Every text/background pair the renderer produces. AA: 4.5 for text (all labels are under 18px), 3 for icons.
export function contrastPairs(t) {
  const pairs = [];
  const add = (what, fg, bg, min = 4.5) => pairs.push({ what, fg, bg, min, ratio: contrast(fg, bg) });
  for (const c of CARD_CLASSES) {
    const k = t.classes[c];
    add(`${c} title`, k.text, k.fill);
    add(`${c} subtitle`, t.muted, k.fill);
    add(`${c} icon`, t.icon, k.fill, 3);
  }
  add("edge label", t.edgeText, t.canvas);
  add("group caption", t.cluster.text, t.cluster.fill);
  add("note", t.note.text, t.note.fill);
  add("text on canvas", t.text, t.canvas);
  (t.scale || []).forEach((s, i) => add(`scale ${i}`, s.text, s.fill));
  return pairs;
}
