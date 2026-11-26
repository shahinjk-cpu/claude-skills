// ```mermaid blocks in Markdown: find them, and swap them for image links once rendered.

const FENCE = /^([ \t]*)(`{3,}|~{3,})[ \t]*mermaid[ \t]*\r?\n([\s\S]*?)\r?\n\1\2[ \t]*$/gm;

export function mermaidBlocks(md) {
  return [...md.matchAll(FENCE)].map((m, i) => ({ index: i + 1, start: m.index, end: m.index + m[0].length, indent: m[1], code: m[3] }));
}

// replacements: [{ start, end, indent, alt, src }]
export function replaceBlocks(md, replacements) {
  let out = md;
  for (const r of [...replacements].sort((a, b) => b.start - a.start))
    out = out.slice(0, r.start) + `${r.indent}![${r.alt.replace(/[[\]]/g, "")}](${r.src})` + out.slice(r.end);
  return out;
}
