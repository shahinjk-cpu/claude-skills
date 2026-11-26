// Turns a theme (themes/*.json) into Mermaid config, classDefs and CSS.
import fs from "node:fs";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
// Package folders, resolved the Node way so this works from a clone, a global install or npx.
export const pkgDir = (name) => path.dirname(require.resolve(`${name}/package.json`));

const b64 = (f) => fs.readFileSync(f).toString("base64");
let interCss = null;
export function fontCss(theme) {
  if (theme.font !== "Inter") return ""; // other fonts must be installed on the machine that views the SVG
  interCss ??= [400, 500, 600].map((w) => `@font-face{font-family:'Inter';font-style:normal;font-weight:${w};font-display:block;` +
    `src:url(data:font/woff2;base64,${b64(path.join(pkgDir("@fontsource/inter"), "files", `inter-latin-${w}-normal.woff2`))}) format('woff2');}`).join("");
  return interCss;
}
const family = (t) => `'${t.font}', Inter, system-ui, sans-serif`;

export function icon(name, color) {
  const f = path.join(pkgDir("lucide-static"), "icons", `${name}.svg`);
  if (!fs.existsSync(f)) throw new Error(`Unknown Lucide icon "${name}". Browse names at https://lucide.dev/icons`);
  const svg = fs.readFileSync(f, "utf8").replace(/<!--[\s\S]*?-->/g, "")
    .replace(/stroke="currentColor"/, `stroke="${color}"`).replace(/stroke-width="2"/, 'stroke-width="1.75"');
  return `<img class='ic' width='16' height='16' src='data:image/svg+xml;base64,${Buffer.from(svg).toString("base64")}'/>`;
}

// Diagram kind from the first meaningful line (skips %% comments and --- front matter).
export function diagramKind(src) {
  const lines = src.split("\n").map((l) => l.trim());
  let i = 0;
  if (lines[0] === "---") { i = lines.indexOf("---", 1) + 1; }
  const first = lines.slice(i).find((l) => l && !l.startsWith("%%")) || "";
  const m = first.match(/^(flowchart|graph|stateDiagram(?:-v2)?|erDiagram|sequenceDiagram|timeline|mindmap|classDiagram|journey|gantt|pie)\b/);
  if (!m) return "other";
  return { graph: "flowchart", "stateDiagram-v2": "state", stateDiagram: "state", erDiagram: "er", sequenceDiagram: "sequence", classDiagram: "class" }[m[1]] || m[1];
}

// Card classes as classDef lines (flowchart and state diagrams accept the same syntax).
export function classDefs(t) {
  return Object.entries(t.classes).map(([name, c]) =>
    `classDef ${name} fill:${c.fill},stroke:${c.stroke},color:${c.text}${c.dash ? `,stroke-dasharray:${c.dash}` : ""}`).join("\n");
}

// Colour sequence for timeline sections and mindmap branches.
const SCALE = ["lav", "sky", "mint", "peach", "yellow", "grey"];

export function mermaidConfig(t) {
  const c = t.classes;
  const scaleVars = {};
  for (let i = 0; i < 12; i++) {
    const k = c[SCALE[i % SCALE.length]];
    Object.assign(scaleVars, { [`cScale${i}`]: k.fill, [`cScalePeer${i}`]: k.stroke, [`cScaleLabel${i}`]: k.text, [`cScaleInv${i}`]: k.stroke });
  }
  return {
    startOnLoad: false, theme: "base", securityLevel: "loose", htmlLabels: true,
    flowchart: { curve: "basis", htmlLabels: true, nodeSpacing: 34, rankSpacing: 52, padding: 14, diagramPadding: 18, wrappingWidth: 260, subGraphTitleMargin: { top: 12, bottom: 8 } },
    state: { padding: 12, nodeSpacing: 40, rankSpacing: 50 },
    er: { diagramPadding: 18, entityPadding: 14, fontSize: 13, useMaxWidth: true },
    sequence: { actorFontFamily: t.font, messageFontFamily: t.font, noteFontFamily: t.font, mirrorActors: false,
                actorFontSize: 13, messageFontSize: 12, noteFontSize: 12, width: 140, height: 44, boxMargin: 8, messageMargin: 34 },
    timeline: { padding: 8, disableMulticolor: false },
    mindmap: { padding: 14 },
    themeVariables: {
      darkMode: t.dark, fontFamily: family(t), fontSize: "13px", background: t.canvas,
      primaryColor: c.lav.fill, primaryBorderColor: c.lav.stroke, primaryTextColor: c.lav.text,
      secondaryColor: c.mint.fill, secondaryBorderColor: c.mint.stroke, secondaryTextColor: c.mint.text,
      tertiaryColor: t.canvas, tertiaryBorderColor: t.cluster.stroke, tertiaryTextColor: t.text,
      mainBkg: c.lav.fill, nodeBorder: c.lav.stroke, nodeTextColor: c.lav.text, textColor: t.text, titleColor: t.text,
      lineColor: t.line, clusterBkg: t.cluster.fill, clusterBorder: t.cluster.stroke, edgeLabelBackground: "transparent",
      actorBkg: c.lav.fill, actorBorder: c.lav.stroke, actorTextColor: c.lav.text, actorLineColor: t.lifeline,
      signalColor: t.line, signalTextColor: t.text, labelTextColor: t.text, loopTextColor: t.text,
      noteBkgColor: t.note.fill, noteBorderColor: t.note.stroke, noteTextColor: t.note.text,
      activationBkgColor: c.sky.fill, activationBorderColor: c.sky.stroke,
      // state diagrams
      labelColor: t.text, altBackground: t.cluster.fill, compositeBackground: t.cluster.fill, compositeTitleBackground: t.cluster.fill,
      compositeBorder: t.cluster.stroke, innerEndBackground: t.line, specialStateColor: t.line, transitionColor: t.line, transitionLabelColor: t.edgeText,
      stateLabelColor: c.lav.text, stateBkg: c.lav.fill,
      // ER diagrams
      attributeBackgroundColorOdd: t.canvas, attributeBackgroundColorEven: c.grey.fill,
      ...scaleVars,
    },
  };
}

export function themeCss(t) {
  const sw = t.strokeWidth, lw = t.lineWidth;
  return `
${fontCss(t)}
svg { font-family: ${family(t)}; }
.label, .nodeLabel, .edgeLabel, .cluster-label, text { font-family: ${family(t)} !important; }
.nodeLabel { font-size: 13px; line-height: 1.35; color: ${t.text}; }
.nodeLabel b { font-weight: 600; }
.nodeLabel .s { display: inline-block; color: ${t.muted}; font-size: 11.5px; margin-top: 2px; }
.ic { width: 16px; height: 16px; vertical-align: -3px; margin-right: 6px; }
.edgeLabel { font-size: 11px; color: ${t.edgeText}; background: transparent; } .edgeLabel rect { fill: transparent !important; } .labelBkg { background: transparent !important; }
.edgeLabel span { background: transparent !important; color: ${t.edgeText} !important; }
.edgeLabel p { background: ${t.canvas} !important; color: ${t.edgeText} !important; padding: 1px 4px; border-radius: 4px; margin: 0; }
.flowchart-link, .transition, .relationshipLine, .edgePaths path { stroke: ${t.line} !important; stroke-width: ${lw}px !important; }
marker path, marker circle { stroke: ${t.line} !important; } marker path { fill: ${t.line} !important; }
marker.er path, marker[id*="er-"] path, marker[id*="_er"] path { fill: none !important; } marker[id*="er-"] circle { fill: ${t.canvas} !important; }
.cluster rect { stroke-width: ${sw}px !important; }
.cluster-label .nodeLabel, .cluster-label span { font-weight: 600; font-size: 12px; color: ${t.cluster.text} !important; letter-spacing: .02em; text-transform: uppercase; }
.node rect, .node polygon, .node path, .node circle { stroke-width: ${sw}px !important; stroke-linejoin: round; }
.messageText { font-size: 12px !important; fill: ${t.text} !important; }
.messageLine0, .messageLine1 { stroke: ${t.line} !important; stroke-width: ${lw}px !important; }
.actor { stroke-width: ${sw}px !important; } text.actor > tspan { font-weight: 500; fill: ${t.classes.lav.text} !important; }
.actor-line { stroke: ${t.lifeline} !important; }
.note { stroke-width: ${sw}px !important; } .noteText, .noteText > tspan { fill: ${t.note.text} !important; }
.labelBox { fill: ${t.cluster.fill} !important; stroke: ${t.cluster.stroke} !important; } .labelText, .labelText > tspan, .loopText, .loopText > tspan { fill: ${t.text} !important; }
.loopLine { stroke: ${t.cluster.stroke} !important; }
/* state */
.statediagram-state .divider { stroke: ${t.classes.lav.stroke} !important; }
.state-start, .state-end, .node circle.state-start { fill: ${t.line} !important; stroke: ${t.line} !important; }
.statediagram-cluster rect.outer { fill: ${t.cluster.fill} !important; stroke: ${t.cluster.stroke} !important; }
.statediagram-cluster .inner { fill: ${t.cluster.fill} !important; }
.statediagram-note rect { fill: ${t.note.fill} !important; stroke: ${t.note.stroke} !important; }
/* ER */
.relationshipLabel, .relationshipLabel span, .edgeLabel .relationshipLabel { color: ${t.edgeText} !important; fill: ${t.edgeText} !important; }
.er.entityBox { fill: ${t.classes.lav.fill} !important; stroke: ${t.classes.lav.stroke} !important; }
.label.name .nodeLabel { font-weight: 600; letter-spacing: .02em; }
.row-rect-odd path { fill: ${t.canvas} !important; } .row-rect-even path { fill: ${t.classes.grey.fill} !important; }
/* timeline and mindmap */
line:not([class^="node-line"]) { stroke: ${t.line} !important; }
.eventWrapper .node-bkg { fill: ${t.canvas} !important; }
.section-root rect, .section-root path, .section-root circle, .section-root polygon { fill: ${t.classes.lav.fill} !important; stroke: ${t.classes.lav.stroke} !important; stroke-width: ${t.strokeWidth}px !important; }
.section-root text, .section-root span { fill: ${t.classes.lav.text} !important; color: ${t.classes.lav.text} !important; font-weight: 600; }
.timeline-node text, .section text { font-family: ${family(t)} !important; }
.mindmap-node .nodeLabel, .mindmap-node text { font-size: 13px; }
.mindmap-edges path, .edge-depth-1, .edge-depth-2, .edge-depth-3 { stroke-width: ${lw + 0.6}px !important; }
`;
}
