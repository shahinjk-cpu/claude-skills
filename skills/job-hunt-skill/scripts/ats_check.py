#!/usr/bin/env python3
"""Check a CV PDF the way applicant-tracking systems (ATS) read it, and against a job posting. No model calls.

Most rejections come from screening questions, recruiter keyword/title searches and broken parsing, not from an
AI verdict. This script checks those honestly:
  1. parsing   - selectable text, contact details, standard section headings, dates, glued lines, odd characters,
                 embedded fonts, page count, file name
  2. keywords  - terms the posting asks for: already in the CV / missing but true (in profile.md: safe to add) /
                 missing and not in your profile (do not add; prepare an honest answer)
  3. title     - posting title words vs the CV headline (recruiters search by title)
  4. screening - knockout topics the posting raises (location, work authorisation, salary, years, language...)
                 with your prepared answers from memory.md
It never suggests hidden text, keyword stuffing or skills you don't have.

Usage:
  python3 ats_check.py --cv CV.pdf [--posting posting.txt|URL] [--title "Senior Engineer"] [--workspace WS] [--json]
"""
import argparse, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import insights  # noqa: E402  (VOCAB, term_re, profile_terms)

HEADINGS = {
    "experience": r"experience|work history|employment|experi[êe]ncia|experiencia|trayectoria",
    "education": r"education|academic|forma[çc][ãa]o|educa[çc][ãa]o|educaci[óo]n|formaci[óo]n",
    "skills": r"skills|competencies|technical|compet[êe]ncias|habilidades|conhecimentos|conocimientos|aptitudes",
}
MONTHS = r"jan|feb|fev|mar|apr|abr|may|mai|jun|jul|aug|ago|sep|set|oct|out|nov|dec|dez|ene|dic"
DATE_RANGE = re.compile(rf"(?:(?:{MONTHS})[a-zç]*\.?\s+)?(?:19|20)\d\d\s*[–—-]\s*(?:(?:(?:{MONTHS})[a-zç]*\.?\s+)?(?:19|20)\d\d|present|current|now|atual|presente|hoje|actual)", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+?\d[\d ()-]{7,}\d")
GLUED = re.compile(r"[^\s•▪●◦\-–]([•▪●◦])\s")
ODD = re.compile("[ﬀ-ﬆ�-]")
NICE_HDR = re.compile(  # a section heading, not the word inside a sentence ("salary and bonus", "X is a plus")
    r"(?:^|\n|[.!?]\s)\s*[#*•\-]*\s*(?:nice[- ]to[- ]haves?|bonus points|preferred (?:qualifications|skills|experience)|pluses|"
    r"(?:it'?s |would be )?a plus if|desirable|what would make you exceptional|diferenciais|desej[áa]vel|deseját?veis)\b[^\n.:]{0,40}(?::|\n)", re.I)
NEED_HDR = re.compile(r"requirements|what you.ll need|qualifications|must have|you have|we.re looking for|requisitos|o que buscamos", re.I)
SCREEN = {
    "location": (r"based in|located in|must (?:live|reside)|residen|relocat|on-?site|hybrid|time ?zone|overlap", r"remote|hybrid|based|location|reloca|time ?zone|live"),
    "work authorisation": (r"right to work|authori[sz]ed to work|work permit|visa|sponsor|citizen", r"citizen|passport|visa|work right|authori"),
    "salary": (r"salary|compensation|pay range|expected (?:salary|compensation)|remunera|pretens", r"floor|pay|salary|rate|eur|usd|brl|r\$|ask"),
    "years of experience": (r"\d\+?\s*(?:years|anos|años)", r"years|anos"),
    "language": (r"english|fluent|portuguese|spanish|german|ingl[êe]s", r"english|portuguese|spanish|native|fluent|language"),
    "notice / start": (r"start date|notice period|available (?:to start|from)|immediate", r"notice|start|available"),
}


def need_tools(*tools):
    import shutil
    miss = [t for t in tools if not shutil.which(t)]
    if miss:
        raise SystemExit(f"missing {', '.join(miss)}: install poppler (Debian/Ubuntu: apt install poppler-utils; "
                         "macOS: brew install poppler; Windows: choco install poppler)")


def pdf_text(path, mode="-raw"):
    need_tools("pdftotext", "pdfinfo", "pdffonts")
    r = subprocess.run(["pdftotext", mode, path, "-"], capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"pdftotext failed on {path}: {r.stderr.strip()} (install poppler-utils)")
    return r.stdout


def pdf_meta(path):
    info = subprocess.run(["pdfinfo", path], capture_output=True, text=True).stdout
    fonts = subprocess.run(["pdffonts", path], capture_output=True, text=True).stdout.splitlines()[2:]
    pages = int(re.search(r"Pages:\s+(\d+)", info).group(1)) if re.search(r"Pages:\s+(\d+)", info) else None
    not_embedded = [f.split()[0] for f in fonts if len(f.split()) > 4 and f.split()[-5] == "no"]
    return pages, not_embedded


def parse_checks(cv_path, text, pages, not_embedded):
    out = []  # (level, message): ok / warn / fail
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(text.strip()) < 300:
        return [("fail", "almost no selectable text: the PDF is probably an image or scan. Export it from a text document.")]
    out.append(("ok", f"{len(text.split())} words of selectable text"))
    head = "\n".join(lines[:12])
    out.append(("ok", "email found near the top") if EMAIL.search(head) else ("warn" if EMAIL.search(text) else "fail",
               "email not in the first lines (put contact details in the body, not in a page header)" if EMAIL.search(text) else "no email found"))
    if not PHONE.search(head):
        out.append(("warn", "no phone number near the top"))
    found = {k: any(re.fullmatch(rf"(?:{p})(?:\s+\w+){{0,3}}:?", l, re.I) or (l.isupper() and re.search(p, l, re.I)) for l in lines) for k, p in HEADINGS.items()}
    missing = [k for k, v in found.items() if not v]
    out.append(("ok", "standard section headings found") if not missing else ("warn", "section headings not recognised: " + ", ".join(missing) +
               " (use plain words like Experience, Education, Skills)"))
    dates = DATE_RANGE.findall(text)
    out.append(("ok", f"{len(dates)} date ranges found") if len(dates) >= 2 else ("warn", "few or no parseable date ranges (use 'Mar 2021 – Aug 2025' style)"))
    glued = [l for l in lines if GLUED.search(l)]
    if glued:
        out.append(("warn", f"{len(glued)} glued line(s): a bullet runs into the previous text, e.g. {glued[0][:70]!r}. Add spacing/line break before the list."))
    odd = sorted({c for c in ODD.findall(text)})
    if odd:
        out.append(("warn", "unusual characters (ligatures or missing glyphs): " + " ".join(repr(c) for c in odd)))
    if not_embedded:
        out.append(("warn", "fonts not embedded: " + ", ".join(not_embedded)))
    if pages and pages > 2:
        out.append(("warn", f"{pages} pages: most recruiters skim; keep 1-2 unless the field expects more"))
    name = os.path.basename(cv_path)
    if re.fullmatch(r"(cv|resume|curriculum)[ _-]?\(?\d*\)?\.pdf", name, re.I) or " " in name:
        out.append(("warn", f"file name '{name}': use Firstname_Lastname_CV_Company.pdf"))
    return out


def posting_text(src):
    if not src:
        return ""
    if re.match(r"https?://", src):
        import scan
        code, _, body = scan.fetch_public(src)
        text = re.sub(r"[ \t\xa0]+", " ", scan.strip(body))
        if len(text) < 300:
            raise SystemExit(f"could not read the posting at {src} (HTTP {code}; public http(s) hosts only, and pages built by "
                             "JavaScript come back empty): save the posting text to a file and pass that file to --posting")
        print("(posting read from a web page, which may include menus or other jobs: for exact keywords, save the posting text to a file)",
              file=sys.stderr)
        return text
    if not os.path.exists(src):
        raise SystemExit(f"--posting: no such file {src}")
    import html
    return html.unescape(open(src, encoding="utf-8").read()).replace("\xa0", " ")


def split_posting(text):
    """(need, nice) parts of a posting. Without headers everything counts as 'need'."""
    m = NICE_HDR.search(text)
    return (text[:m.start()], text[m.start():]) if m else (text, "")


RELATED = {  # evidence words in profile.md that support a posting term (shown as "related", never auto-claimed)
    "state estimation": ["kalman"], "tracking": ["kalman", "tracker"], "model deployment": ["deployed", "deployment", "in production"],
    "real-time": ["fps", "real time"], "data pipelines": ["pipeline"], "backend": ["api", "apis", "microservice"],
    "inference": ["onnx", "quantization"], "signal processing": ["image processing", "filtering"],
}


def dnc_line(dnc, rx):
    """The words around the match, so 'robotics policy learning' isn't mistaken for all robotics."""
    for line in dnc.splitlines():
        m = rx.search(line) if hasattr(rx, "pattern") else None
        if m:
            a, b = max(0, m.start() - 40), m.end() + 40
            return ("…" if a else "") + line[a:b].strip() + ("…" if b < len(line) else "")
        if not hasattr(rx, "pattern") and rx.search(line):
            return line.strip("-* ")[:90]
    return ""


def keywords(cv_text, post, cfg, ws):
    vocab = sorted({t.lower() for ts in insights.VOCAB.values() for t in ts}
                   | ({t.lower() for t in cfg["roles"]["textKeywords"] + cfg["roles"]["titleKeywords"] + (cfg.get("skills") or {}).get("extra", [])} if cfg else set()))
    have, dnc = insights.profile_terms(ws) if ws else ("", "")
    need, nice = split_posting(post)
    rows = []
    for t in vocab:
        rx = insights.term_re(t)
        where = "need" if rx.search(need) else "nice" if nice and rx.search(nice) else None
        if not where:
            continue
        note = ""
        if rx.search(cv_text):
            status = "in CV"
        elif have and rx.search(have):
            status = "add (true, in profile)"
        elif dnc and rx.search(dnc):
            status, note = "do not claim", dnc_line(dnc, rx)
        else:
            rel = [w for w in RELATED.get(t, []) if have and re.search(r"\b" + re.escape(w) + r"\b", have, re.I)]
            status, note = ("related evidence", "profile mentions: " + ", ".join(rel)) if rel else ("not in profile", "")
        rows.append({"term": t, "where": where, "status": status, "note": note})
    needed = [r for r in rows if r["where"] == "need"]
    cov = sum(r["status"] == "in CV" for r in needed)
    return rows, (cov, len(needed))


def title_check(cv_text, title):
    if not title:
        return None
    lines = [l.strip() for l in cv_text.splitlines() if l.strip()]
    headline = lines[1] if len(lines) > 1 else ""
    words = lambda s: {w for w in re.findall(r"[a-zà-ú+#]+", s.lower()) if len(w) > 2 and w not in {"and", "the", "for", "with", "e", "de"}}  # noqa: E731
    t, h = words(title), words(headline)
    return {"title": title, "headline": headline, "shared": sorted(t & h), "missing": sorted(t - h)}


def screening(post, ws):
    mem = open(os.path.join(ws, "memory.md"), encoding="utf-8").read() if ws and os.path.exists(os.path.join(ws, "memory.md")) else ""
    bullets = [l.strip("-* ").strip() for l in mem.splitlines() if l.strip().startswith(("-", "*"))]
    out = []
    for topic, (in_post, in_mem) in SCREEN.items():
        m = re.search(in_post, post, re.I)
        if not m:
            continue
        snippet = post[max(0, m.start() - 60):m.end() + 60].replace("\n", " ").strip()
        answers = [b for b in bullets if re.search(in_mem, b, re.I)][:3]
        out.append({"topic": topic, "posting": snippet, "your_rules": answers})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cv", required=True)
    ap.add_argument("--posting", help="posting text file or URL")
    ap.add_argument("--title", help="job title as posted")
    ap.add_argument("--workspace", help="workspace (profile.md, memory.md, filters.md)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    ws = os.path.abspath(os.path.expanduser(a.workspace)) if a.workspace else None
    cfg = None
    if ws:
        from config import load_config
        cfg = load_config(ws, require_queries=False)
    text = pdf_text(a.cv)
    pages, not_emb = pdf_meta(a.cv)
    report = {"parsing": parse_checks(a.cv, text, pages, not_emb)}
    post = posting_text(a.posting)
    if post:
        rows, (cov, n) = keywords(text, post, cfg, ws)
        report.update(keywords=rows, coverage=[cov, n], title=title_check(text, a.title), screening=screening(post, ws))
    if a.json:
        print(json.dumps(report, ensure_ascii=False, indent=1))
        return
    mark = {"ok": "✅", "warn": "⚠ ", "fail": "❌"}
    print("1. Parsing (what an ATS reads)")
    for lvl, msg in report["parsing"]:
        print(f"   {mark[lvl]} {msg}")
    if not post:
        print("\n(add --posting to check keywords, title and screening topics)")
        return
    cov, n = report["coverage"]
    print(f"\n2. Keywords from the posting: {cov}/{n} required terms already in the CV")
    for label, st in (("Missing but true (in profile.md): add them where they fit", "add (true, in profile)"),
                      ("Missing, not in your profile: do NOT add; prepare an honest answer", "not in profile"),
                      ("Related evidence in your profile: describe what you did, in the posting's words only if accurate", "related evidence"),
                      ("Listed in 'Do NOT claim': don't add (check the exact line)", "do not claim"),
                      ("Already in the CV", "in CV")):
        items = [f"{r['term']}{' (nice)' if r['where'] == 'nice' else ''}{' [' + r['note'] + ']' if r.get('note') else ''}" for r in report["keywords"] if r["status"] == st]
        if items:
            print(f"   {label}:\n      " + ", ".join(items))
    t = report.get("title")
    if t:
        print(f"\n3. Title: posting '{t['title']}' vs CV headline '{t['headline']}'")
        print(f"   shared words: {', '.join(t['shared']) or '-'} | missing: {', '.join(t['missing']) or '-'}"
              + ("  → if it's truthful, echo the posting's title in your headline" if t["missing"] else ""))
    if report["screening"]:
        print("\n4. Screening topics in the posting (answer these consistently; they're where most auto-rejections happen)")
        for s in report["screening"]:
            print(f"   • {s['topic']}: “…{s['posting'][:110]}…”")
            for r in s["your_rules"]:
                print(f"       your rule: {r[:110]}")
    print("\nNever add hidden text, keyword lists or skills you don't have: ATS and recruiters catch it, and it breaks trust.")


if __name__ == "__main__":
    main()
