#!/usr/bin/env python3
"""render_report.py: turn DIR/findings.json into a publishable audit page.

Writes DIR/report/index.html, DIR/report/img/*.jpg and DIR/report/report.md, and prints the
Artifact publish arguments (file_path + files map). Marks are drawn as SVG over the frame, in
displayed-frame pixel coordinates, so they stay sharp and line up at any page width.

findings.json (written by Claude, see references/report.md for the full schema):
{
  "title": "Sign-up flow audit", "subject": "...", "summary": "...",
  "top_fixes": ["..."], "evidence_limits": ["..."], "not_assessable": ["..."],
  "positives": ["..."], "dismissed": ["..."], "next_checks": ["..."],
  "timeline": [{"time": 0.0, "screen": "...", "change": "..."}],
  "findings": [{
     "id": "F-01", "severity": "P2", "confidence": "High", "title": "...", "check": "TERM-DRIFT",
     "screen": "...", "time": "00:05-00:06",
     "evidence": [{"time": 6.0, "caption": "...", "marks": [{"x":0,"y":84,"w":160,"h":60,"label":"1"}]}],
     "observation": "...", "expected": "...", "impact": "...", "cause": "...",
     "fix": {"summary": "...", "steps": ["..."], "effort": "S", "verify": "...",
             "changes": [{"what": "Panel title", "before": "Sessions", "after": "Chats"}]}
  }]
}
"""
import html
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rec_audit as ra  # noqa: E402

SEV_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
SEV_NAME = {"P0": "Blocker", "P1": "Major", "P2": "Minor", "P3": "Polish"}


def e(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def zoom_box(marks, w, h):
    """Padded view box around all marks, kept to the frame's aspect ratio where possible."""
    x0 = min(m["x"] for m in marks); y0 = min(m["y"] for m in marks)
    x1 = max(m["x"] + m["w"] for m in marks); y1 = max(m["y"] + m["h"] for m in marks)
    bw, bh = x1 - x0, y1 - y0
    aspect = w / float(h)
    zw = max(bw * 1.8, w * 0.22)
    zh = max(bh * 1.8, zw / aspect)
    zw = max(zw, zh * aspect * 0.75)
    zw, zh = min(zw, w), min(zh, h)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    zx = min(max(0, cx - zw / 2), w - zw)
    zy = min(max(0, cy - zh / 2), h - zh)
    return zx, zy, zw, zh


def marks_svg(marks, scale):
    """Ellipse rings + numbered badges. scale = stroke size unit in viewBox px."""
    out = []
    for k, m in enumerate(marks):
        pad = 6 * scale
        cx = m["x"] + m["w"] / 2.0
        cy = m["y"] + m["h"] / 2.0
        rx = m["w"] / 2.0 + pad
        ry = m["h"] / 2.0 + pad
        label = m.get("label") or str(k + 1)
        out.append('<ellipse class="halo" cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" stroke-width="%.1f"/>'
                   % (cx, cy, rx, ry, 7 * scale))
        out.append('<ellipse class="ring" cx="%.1f" cy="%.1f" rx="%.1f" ry="%.1f" stroke-width="%.1f"/>'
                   % (cx, cy, rx, ry, 3.2 * scale))
        bx = cx + rx * 0.707
        by = cy - ry * 0.707
        r = 11 * scale
        out.append('<circle class="badge" cx="%.1f" cy="%.1f" r="%.1f" stroke-width="%.1f"/>' % (bx, by, r, 2.4 * scale))
        out.append('<text class="badge-t" x="%.1f" y="%.1f" font-size="%.1f">%s</text>'
                   % (bx, by + 4.6 * scale, 13 * scale, e(label)))
    return "".join(out)


def figure(img_rel, w, h, marks, caption, t_label, alt):
    s = w / 900.0
    main = ('<svg class="shot" viewBox="0 0 %d %d" role="img" aria-label="%s">'
            '<image href="%s" x="0" y="0" width="%d" height="%d"/>%s</svg>'
            % (w, h, e(alt), e(img_rel), w, h, marks_svg(marks, s) if marks else ""))
    zoom = ""
    if marks:
        zx, zy, zw, zh = zoom_box(marks, w, h)
        zs = zw / 520.0
        zoom = ('<figure class="zoom"><svg viewBox="%.1f %.1f %.1f %.1f" style="aspect-ratio:%.4f" role="img" '
                'aria-label="Close-up of the marked area"><image href="%s" x="0" y="0" width="%d" height="%d"/>%s</svg>'
                '<figcaption>Close-up</figcaption></figure>'
                % (zx, zy, zw, zh, zw / zh, e(img_rel), w, h, marks_svg(marks, zs)))
    return ('<div class="evidence"><figure class="frame">%s<figcaption><span class="tc">%s</span> %s</figcaption>'
            '</figure>%s</div>' % (main, e(t_label), e(caption), zoom))


MOCK_BASE = """<style>:host{display:block;contain:content}*{box-sizing:border-box}
.chg{outline:2px dashed #12a37f;outline-offset:3px;border-radius:6px}
.mock-root{font:14px/1.45 system-ui,-apple-system,"Segoe UI",sans-serif}</style>"""


def mock_block(m):
    """Live HTML mock-up of the fixed screen, isolated in a declarative shadow root."""
    if not m or not m.get("html"):
        return ""
    body = m["html"].replace("</template", "&lt;/template")
    css = (m.get("css") or "").replace("</style", "")
    cap = m.get("caption") or "Mock-up of the fixed screen"
    return ('<figure class="mock"><div class="mock-host"><template shadowrootmode="open">%s<style>%s</style>'
            '<div class="mock-root">%s</div></template></div><figcaption><span class="legend"></span>%s</figcaption></figure>'
            % (MOCK_BASE, css, body, e(cap)))


def li(items):
    return "".join("<li>%s</li>" % e(x) for x in items)


def render(d):
    d = os.path.abspath(d)
    meta, an = ra.load_cache(d)
    pts = meta["pts"]
    w, h = an["probe"]["w"], an["probe"]["h"]
    with open(os.path.join(d, "findings.json")) as f:
        rep = json.load(f)
    out = os.path.join(d, "report")
    img = os.path.join(out, "img")
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(img)
    fdir = os.path.join(d, "cache", "frames")

    findings = sorted(rep.get("findings", []), key=lambda f: (SEV_ORDER.get(f.get("severity"), 9), f.get("id", "")))
    # extract every evidence frame once
    need = {}
    for f in findings:
        for ev in f.get("evidence", []):
            i = ra.nearest_frame(pts, float(ev["time"]))
            need[i] = True
    ra.extract_frames(an["video"], list(need), fdir)
    saved = {}
    for i in need:
        name = "t_%s.jpg" % ra.ft(pts[i]).replace(":", "-").replace(".", "_")
        ra.save_capped(os.path.join(fdir, "f_%06d.jpg" % i), os.path.join(img, name))
        saved[i] = "img/" + name

    counts = {}
    for f in findings:
        counts[f.get("severity")] = counts.get(f.get("severity"), 0) + 1
    chips = "".join('<span class="sev sev-%s">%s %s <b>%d</b></span>' % (s.lower(), s, SEV_NAME[s], counts[s])
                    for s in ("P0", "P1", "P2", "P3") if counts.get(s))
    if rep.get("positives"):
        chips += '<span class="sev sev-ok">Works well <b>%d</b></span>' % len(rep["positives"])

    index = "".join(
        '<li><a href="#%s"><span class="sev sev-%s">%s</span><span class="ix-t">%s</span>'
        '<span class="tc">%s</span></a></li>'
        % (e(f["id"].lower()), e(f.get("severity", "").lower()), e(f.get("severity")), e(f["id"] + " · " + f["title"]),
           e(f.get("time", ""))) for f in findings)

    cards = []
    for f in findings:
        evs = []
        for k, ev in enumerate(f.get("evidence", [])):
            i = ra.nearest_frame(pts, float(ev["time"]))
            evs.append(figure(saved[i], w, h, ev.get("marks") or [], ev.get("caption", ""), ra.ft(pts[i]),
                              "%s, frame at %s" % (f["title"], ra.ft(pts[i]))))
        fix = f.get("fix") or {}
        changes = ""
        if fix.get("changes"):
            rows = "".join('<div class="chg"><div class="chg-what">%s</div><div class="chg-b"><span>Now</span>%s</div>'
                           '<div class="chg-a"><span>Change to</span>%s</div></div>'
                           % (e(c.get("what")), e(c.get("before")), e(c.get("after"))) for c in fix["changes"])
            changes = '<div class="changes">%s</div>' % rows
        steps = '<ol class="steps">%s</ol>' % li(fix["steps"]) if fix.get("steps") else ""
        code = ""
        if fix.get("code_refs"):
            code = '<div class="code"><p class="code-h">Where in the code</p><ul>%s</ul></div>' % "".join(
                '<li><span class="mono path">%s%s</span>%s</li>' % (
                    e(c.get("file")), (":%s" % e(c["line"])) if c.get("line") else "",
                    (' <span class="code-n">%s</span>' % e(c["note"])) if c.get("note") else "") for c in fix["code_refs"])
        meta_bits = []
        if fix.get("effort"):
            meta_bits.append('<span class="pill">Effort %s</span>' % e(fix["effort"]))
        if f.get("check"):
            meta_bits.append('<span class="pill mono">%s</span>' % e(f["check"]))
        verify = '<p class="verify"><b>Check it worked:</b> %s</p>' % e(fix["verify"]) if fix.get("verify") else ""
        facts = []
        for key, lab in (("observation", "What the recording shows"), ("expected", "Expected"),
                         ("impact", "Cost to the user"), ("cause", "Likely cause (inferred)")):
            if f.get(key):
                facts.append("<dt>%s</dt><dd>%s</dd>" % (lab, e(f[key])))
        cards.append(
            '<article class="finding" id="%s"><header class="f-head"><span class="sev sev-%s">%s · %s</span>'
            '<span class="conf">%s confidence</span><h3>%s <span class="fid">%s</span></h3>'
            '<p class="where"><span class="tc">%s</span> %s</p></header>'
            '<div class="f-body"><section class="issue" aria-label="Issue">%s<dl class="facts">%s</dl></section>'
            '<aside class="fix" aria-label="Suggested fix"><p class="eyebrow">Suggested fix</p><p class="fix-sum">%s</p>'
            '%s<details class="more"%s><summary>Details</summary><div class="more-body">%s%s<div class="fix-meta">%s</div>%s</div></details>'
            '</aside></div></article>'
            % (e(f["id"].lower()), e(f.get("severity", "").lower()), e(f.get("severity")),
               e(SEV_NAME.get(f.get("severity"), "")), e(f.get("confidence", "")), e(f["title"]), e(f["id"]),
               e(f.get("time", "")), e(f.get("screen", "")), "".join(evs), "".join(facts),
               e(fix.get("summary", "")), mock_block(fix.get("mock")) + code, "" if fix.get("mock") else " open",
               changes, steps, "".join(meta_bits), verify))

    timeline = ""
    if rep.get("timeline"):
        rows = "".join("<tr><td class=\"tc\">%s</td><td>%s</td><td>%s</td></tr>"
                       % (e(ra.ft(float(t["time"]))), e(t.get("screen")), e(t.get("change"))) for t in rep["timeline"])
        timeline = ('<section class="block"><h2>Timeline</h2><div class="tablewrap"><table><thead><tr><th>Time</th>'
                    '<th>Screen</th><th>What changed</th></tr></thead><tbody>%s</tbody></table></div></section>' % rows)

    def listblock(key, heading, cls=""):
        if not rep.get(key):
            return ""
        return '<section class="block %s"><h2>%s</h2><ul>%s</ul></section>' % (cls, heading, li(rep[key]))

    iv = an["interval_ms"]
    prov = ("%s · %dx%d · %.1f s · %d frames · timing resolution about ±%d ms"
            % (os.path.basename(an["video"]), w, h, an["probe"]["duration"], an["frames"],
               round(iv["median_during_motion"])))
    top = '<ol class="top">%s</ol>' % li(rep["top_fixes"]) if rep.get("top_fixes") else ""

    fams = []
    for f in findings:
        for fam in ((f.get("fix") or {}).get("mock") or {}).get("fonts") or []:
            if fam not in fams:
                fams.append(fam)
    mock_fonts = ""
    if fams:
        q = "&".join("family=%s:wght@400;500;600;700" % fam.replace(" ", "+") for fam in fams)
        mock_fonts = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?%s&display=swap">' % e(q)
    page = TEMPLATE.format(mock_fonts=mock_fonts,
        title=e(rep.get("title", "Recording audit")), subject=e(rep.get("subject", "")),
        prov=e(prov), chips=chips, summary=e(rep.get("summary", "")), top=top, index=index,
        cards="".join(cards) or '<p class="none">No findings. An empty list is a valid result.</p>',
        works=listblock("positives", "What works", "works"), timeline=timeline,
        limits=listblock("evidence_limits", "Evidence limits"),
        na=listblock("not_assessable", "Not assessable from this recording"),
        dismissed=listblock("dismissed", "Signals checked and dismissed"),
        nextc=listblock("next_checks", "Recommended next checks"))
    with open(os.path.join(out, "index.html"), "w") as fh:
        fh.write(page)
    write_md(rep, findings, os.path.join(out, "report.md"), prov)
    files = {v: os.path.join(out, v) for v in saved.values()}
    print("page: %s" % os.path.join(out, "index.html"))
    print("publish with the Artifact tool: file_path=%s files=%s"
          % (os.path.join(out, "index.html"), json.dumps(files)))


def write_md(rep, findings, path, prov):
    L = ["# %s" % rep.get("title", "Recording audit"), "", prov, "", rep.get("summary", ""), ""]
    for f in findings:
        fix = f.get("fix") or {}
        L.append("## [%s · %s] %s · %s" % (f.get("severity"), f.get("confidence"), f["id"], f["title"]))
        L.append("- Where: %s · %s · check %s" % (f.get("time"), f.get("screen"), f.get("check")))
        for key, lab in (("observation", "Observation"), ("expected", "Expected"), ("impact", "Impact"),
                         ("cause", "Likely cause (inferred)")):
            if f.get(key):
                L.append("- %s: %s" % (lab, f[key]))
        L.append("- Fix: %s" % fix.get("summary", ""))
        for s in fix.get("steps", []):
            L.append("  - %s" % s)
        for c in fix.get("changes", []):
            L.append("  - %s: \"%s\" -> \"%s\"" % (c.get("what"), c.get("before"), c.get("after")))
        if fix.get("verify"):
            L.append("- Verify: %s" % fix["verify"])
        L.append("")
    for key, lab in (("positives", "What works"), ("evidence_limits", "Evidence limits"),
                     ("not_assessable", "Not assessable"), ("dismissed", "Signals dismissed"),
                     ("next_checks", "Next checks")):
        if rep.get(key):
            L.append("## " + lab)
            L += ["- " + x for x in rep[key]]
            L.append("")
    with open(path, "w") as fh:
        fh.write("\n".join(L))


TEMPLATE = """<title>{title}</title>
<meta name="claude:viewport-fit-sides" content="cover">
<link rel="preconnect" href="https://fonts.googleapis.com">
{mock_fonts}
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wght@12..96,600;12..96,700&family=IBM+Plex+Sans:wght@400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
/* Layout: an inspection sheet. Summary and index first, then one card per finding:
   the marked screen on the left, the suggested fix on the right, stacked on phones. */
:root {{
  --bg: #f3f4f7; --surface: #ffffff; --ink: #16191f; --muted: #5a6170; --line: #dde0e7;
  --mark: #e5195e; --mark-halo: #ffffff; --fix: #0f6b5a; --fix-bg: #e9f5f1;
  --p0: #b3123b; --p1: #c2410c; --p2: #a16207; --p3: #475569; --ok: #15803d;
  --chip-bg: #eceef3;
  --display: "Bricolage Grotesque", "Avenir Next", system-ui, sans-serif;
  --body: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --mono: "IBM Plex Mono", ui-monospace, "SF Mono", Menlo, monospace;
}}
@media (prefers-color-scheme: dark) {{ :root:not([data-theme="light"]) {{
  --bg: #101217; --surface: #181b22; --ink: #e9ebf0; --muted: #a0a6b3; --line: #2a2f3a;
  --mark: #ff4f86; --mark-halo: #101217; --fix: #5fd3b5; --fix-bg: #12261f;
  --p0: #ff6b8a; --p1: #ff9a5c; --p2: #f2c14e; --p3: #a3b1c6; --ok: #5bd98a; --chip-bg: #232733;
  color-scheme: dark; }} }}
:root[data-theme="dark"] {{
  --bg: #101217; --surface: #181b22; --ink: #e9ebf0; --muted: #a0a6b3; --line: #2a2f3a;
  --mark: #ff4f86; --mark-halo: #101217; --fix: #5fd3b5; --fix-bg: #12261f;
  --p0: #ff6b8a; --p1: #ff9a5c; --p2: #f2c14e; --p3: #a3b1c6; --ok: #5bd98a; --chip-bg: #232733;
  color-scheme: dark; }}
body {{ background: var(--bg); color: var(--ink); font: 15px/1.55 var(--body); }}
.wrap {{ max-width: 1180px; margin: 0 auto; padding-block: 32px 64px;
  padding-left: max(16px, env(safe-area-inset-left, 0px)); padding-right: max(16px, env(safe-area-inset-right, 0px));
  display: grid; gap: 28px; }}
h1, h2, h3 {{ font-family: var(--display); text-wrap: balance; margin: 0; letter-spacing: -0.01em; }}
h1 {{ font-size: clamp(28px, 4vw, 40px); line-height: 1.1; }}
h2 {{ font-size: 20px; }}
h3 {{ font-size: 19px; line-height: 1.3; }}
p {{ margin: 0; }}
.tc, .mono {{ font-family: var(--mono); font-size: 12.5px; font-variant-numeric: tabular-nums; }}
.tc {{ color: var(--muted); }}
.masthead {{ display: grid; gap: 12px; }}
.eyebrow {{ font: 600 11.5px/1 var(--body); text-transform: uppercase; letter-spacing: 0.09em; color: var(--muted); }}
.subject {{ color: var(--muted); max-width: 70ch; }}
.chips {{ display: flex; flex-wrap: wrap; gap: 8px; }}
.sev {{ display: inline-flex; align-items: center; gap: 6px; padding: 3px 9px; border-radius: 999px;
  font: 600 12px/1.5 var(--body); background: var(--chip-bg); color: var(--p3); white-space: nowrap; }}
.sev b {{ font-variant-numeric: tabular-nums; }}
.sev-p0 {{ color: var(--p0); }} .sev-p1 {{ color: var(--p1); }} .sev-p2 {{ color: var(--p2); }}
.sev-p3 {{ color: var(--p3); }} .sev-ok {{ color: var(--ok); }}
.sev::before {{ content: ""; width: 7px; height: 7px; border-radius: 50%; background: currentColor; }}
.overview {{ display: grid; grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 20px; }}
.panel {{ background: var(--surface); border: 1px solid var(--line); border-radius: 10px; padding: 18px 20px; display: grid; gap: 10px; align-content: start; min-width: 0; }}
.top {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; }}
.index {{ list-style: none; margin: 0; padding: 0; display: grid; }}
.index a {{ display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: 10px; align-items: center;
  padding: 8px 4px; border-bottom: 1px solid var(--line); color: inherit; text-decoration: none; }}
.index li:last-child a {{ border-bottom: 0; }}
.index a:hover .ix-t, .index a:focus-visible .ix-t {{ text-decoration: underline; }}
.ix-t {{ min-width: 0; }}
a:focus-visible {{ outline: 2px solid var(--mark); outline-offset: 2px; border-radius: 4px; }}
.finding {{ background: var(--surface); border: 1px solid var(--line); border-radius: 12px; overflow: hidden; scroll-margin-top: 16px; }}
.f-head {{ padding: 18px 22px 14px; display: grid; gap: 6px; border-bottom: 1px solid var(--line); }}
.f-head .sev {{ justify-self: start; }}
.conf {{ font-size: 12.5px; color: var(--muted); }}
.f-head .sev + .conf {{ margin-top: -2px; }}
.fid {{ font: 500 13px var(--mono); color: var(--muted); margin-left: 4px; }}
.where {{ color: var(--muted); }}
.f-body {{ display: grid; grid-template-columns: minmax(0, 1.25fr) minmax(0, 1fr); }}
.issue {{ padding: 18px 22px 22px; display: grid; gap: 16px; align-content: start; min-width: 0; }}
.fix {{ padding: 18px 22px 22px; background: var(--fix-bg); border-left: 1px solid var(--line); display: grid; gap: 12px; align-content: start; min-width: 0; }}
.fix .eyebrow {{ color: var(--fix); }}
.fix-sum {{ font-weight: 600; font-size: 16px; line-height: 1.45; }}
.evidence {{ display: grid; gap: 10px; }}
figure {{ margin: 0; display: grid; gap: 6px; }}
figcaption {{ font-size: 13px; color: var(--muted); }}
.shot, .zoom svg {{ width: 100%; height: auto; display: block; border-radius: 6px; border: 1px solid var(--line); background: var(--bg); }}
.zoom {{ max-width: 360px; }}
.halo {{ fill: none; stroke: var(--mark-halo); stroke-opacity: 0.9; }}
.ring {{ fill: none; stroke: var(--mark); }}
.badge {{ fill: var(--mark); stroke: var(--mark-halo); }}
.badge-t {{ fill: #ffffff; font-family: var(--body); font-weight: 700; text-anchor: middle; }}
.facts {{ margin: 0; display: grid; gap: 10px; }}
.facts dt {{ font-weight: 600; font-size: 13px; }}
.facts dd {{ margin: 2px 0 0; color: var(--ink); max-width: 68ch; }}
.changes {{ display: grid; gap: 10px; }}
.chg {{ display: grid; gap: 4px; background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }}
.chg-what {{ font-size: 12.5px; color: var(--muted); font-weight: 600; }}
.chg-b, .chg-a {{ display: grid; grid-template-columns: 74px minmax(0, 1fr); gap: 8px; font-family: var(--mono); font-size: 13px; }}
.chg-b span, .chg-a span {{ font-family: var(--body); font-size: 11.5px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); padding-top: 2px; }}
.chg-b {{ text-decoration: line-through; text-decoration-color: var(--mark); color: var(--muted); }}
.chg-b span {{ text-decoration: none; }}
.chg-a {{ color: var(--fix); font-weight: 500; }}
.steps {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; }}
.fix-meta {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.pill {{ padding: 2px 8px; border-radius: 999px; background: var(--surface); border: 1px solid var(--line); font-size: 12px; }}
.verify {{ font-size: 13.5px; color: var(--muted); }}
.verify b {{ color: var(--ink); }}
.findings {{ display: grid; gap: 22px; }}
.code {{ display: grid; gap: 6px; }}
.code-h {{ font-weight: 600; font-size: 13px; }}
.code ul {{ margin: 0; padding: 0; list-style: none; display: grid; gap: 6px; }}
.code li {{ display: grid; gap: 2px; padding: 8px 10px; border-radius: 8px; background: var(--surface); border: 1px solid var(--line); min-width: 0; }}
.path {{ overflow-wrap: anywhere; color: var(--ink); }}
.code-n {{ font-size: 13px; color: var(--muted); }}
.mock {{ gap: 8px; }}
.mock-host {{ border: 1px solid var(--line); border-radius: 10px; overflow: auto; max-width: 100%; background: var(--surface); }}
.legend {{ display: inline-block; width: 18px; height: 10px; border: 2px dashed #12a37f; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }}
.more {{ border-top: 1px solid var(--line); padding-top: 10px; }}
.more summary {{ cursor: pointer; font-weight: 600; font-size: 13.5px; color: var(--fix); }}
.more summary:focus-visible {{ outline: 2px solid var(--mark); outline-offset: 2px; border-radius: 4px; }}
.more-body {{ display: grid; gap: 12px; padding-top: 10px; }}
.block {{ display: grid; gap: 10px; }}
.block ul {{ margin: 0; padding-left: 20px; display: grid; gap: 4px; max-width: 80ch; }}
.works li::marker {{ color: var(--ok); }}
.lower {{ display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 24px 32px; }}
.tablewrap {{ overflow-x: auto; }}
table {{ border-collapse: collapse; width: 100%; font-size: 14px; }}
th, td {{ text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }}
th {{ font-size: 12px; text-transform: uppercase; letter-spacing: 0.06em; color: var(--muted); font-weight: 600; }}
.prov {{ color: var(--muted); }}
@media (max-width: 820px) {{
  .overview, .f-body, .lower {{ grid-template-columns: minmax(0, 1fr); }}
  .fix {{ border-left: 0; border-top: 1px solid var(--line); }}
  .zoom {{ max-width: none; }}
}}
@media (prefers-reduced-motion: no-preference) {{ html {{ scroll-behavior: smooth; }} }}
</style>
<main class="wrap">
  <header class="masthead">
    <p class="eyebrow">Screen recording audit</p>
    <h1>{title}</h1>
    <p class="subject">{subject}</p>
    <p class="prov tc">{prov}</p>
    <div class="chips">{chips}</div>
  </header>
  <section class="overview">
    <div class="panel"><h2>Summary</h2><p>{summary}</p>{top}</div>
    <nav class="panel" aria-label="Findings"><h2>Findings</h2><ul class="index">{index}</ul></nav>
  </section>
  <section class="findings" aria-label="Findings in detail">{cards}</section>
  {works}
  {timeline}
  <div class="lower">{limits}{na}{dismissed}{nextc}</div>
</main>
<script>
document.querySelectorAll("template[shadowrootmode]").forEach(function (t) {{
  var host = t.parentNode;
  if (host.shadowRoot) return;
  try {{ host.attachShadow({{ mode: "open" }}).appendChild(t.content); t.remove(); }} catch (err) {{}}
}});
</script>
"""


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: render_report.py AUDIT_DIR (the folder with analysis.json and findings.json)")
        sys.exit(2)
    render(sys.argv[1])
