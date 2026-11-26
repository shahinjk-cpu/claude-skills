#!/usr/bin/env python3
"""Reports that turn the scans and the outcome log into decisions. Read-only unless you pass --add.

Usage:
  python3 insights.py --workspace WS employers [--days 90] [--suggest-ats] [--add]   # who keeps hiring people like you
  python3 insights.py --workspace WS companies [--company NAME]                     # each company's track record
  python3 insights.py --workspace WS skills [--top 25]                              # market skill gaps
  python3 insights.py --workspace WS weekly [--days 7]                              # search health + one suggestion
  python3 insights.py --workspace WS due                                            # what needs attention today (run at session start)

Small numbers (n < MIN_N) are reported as counts "k/n", never as percentages; each report says so once.
"""
import argparse, collections, datetime as dt, glob, json, os, re, statistics, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import load_config, write_atomic, read_json  # noqa: E402
import eligibility as EL  # noqa: E402
from outcomes import MIN_N, Log, job_id, rate  # noqa: E402

NOT_HIRING_HERE = re.compile(r"onsite|not remote|restricted|company excluded|role excluded|hybrid", re.I)  # stale/repost still count as "they hire"
REPLY = {"screening", "interview", "offer", "hired", "rejected"}
ENDED = {"rejected", "ghosted", "withdrawn", "offer", "hired"}
VOCAB = {  # generic tech vocabulary; users add their own via filters.md -> skills.extra
    "languages": ["python", "c++", "c#", "java", "kotlin", "swift", "go", "r", "rust", "javascript", "typescript", "scala", "matlab", "sql", "bash", "cuda"],
    "ml": ["pytorch", "tensorflow", "keras", "jax", "scikit-learn", "xgboost", "hugging face", "transformers", "onnx", "tensorrt", "openvino", "tflite",
           "quantization", "distillation", "mlflow", "weights & biases", "kubeflow", "dvc", "ray", "triton", "vllm", "llm", "rag", "langchain",
           "reinforcement learning", "diffusion", "vlm", "multimodal", "foundation model", "fine-tuning", "mlops"],
    "vision": ["computer vision", "opencv", "yolo", "detectron", "mmdetection", "object detection", "segmentation", "tracking", "ocr", "pose estimation",
               "slam", "point cloud", "lidar", "depth estimation", "3d", "stereo", "camera calibration", "nerf", "gaussian splatting", "video", "image processing",
               "anomaly detection", "edge", "embedded", "jetson", "sensor fusion", "kalman"],
    "data": ["pandas", "numpy", "spark", "airflow", "dbt", "kafka", "postgresql", "mysql", "mongodb", "redis", "elasticsearch", "bigquery", "snowflake", "databricks"],
    "cloud": ["aws", "gcp", "azure", "sagemaker", "lambda", "s3", "docker", "kubernetes", "terraform", "ci/cd", "linux", "git", "grpc", "rest api", "fastapi", "flask"],
    "systems": ["backend", "microservices", "distributed systems", "data pipelines", "real-time", "streaming", "low latency", "signal processing",
                "state estimation", "numerical methods", "robotics", "ros", "depth camera", "pose estimation", "ml infrastructure", "model deployment",
                "inference", "profiling", "multithreading", "concurrency", "embedded linux", "fpga"],
    "web_mobile": ["react", "next.js", "vue", "angular", "node.js", "django", "ios", "android", "flutter", "react native", "graphql"],
}


# ------------------------------------------------------------------ data
def scan_date(path):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", os.path.basename(path))
    return m.group(1) if m else None


def gross(j):
    p = j.get("pay_monthly") or j.get("brl")
    return (p[0] + p[1]) / 2 if p else None


def load_results(ws, cfg, days=None, today=None):
    """Relevant jobs from every results file, one per job id (newest copy), with first/last seen dates."""
    today = today or dt.date.today()
    jobs = {}
    for path in sorted(glob.glob(os.path.join(ws, "search", "scans", "results-????-??-??.json"))):
        d = scan_date(path)
        if days and (today - dt.date.fromisoformat(d)).days > days:
            continue
        res = read_json(path)
        for j in res.get("keep", []) + res.get("excluded", []):
            jid = job_id(j["company"], j["title"])
            first = jobs[jid]["first_seen"] if jid in jobs else d
            j = dict(j, first_seen=first, last_seen=d, job=jid)
            if not j.get("eligibility") and cfg["person"].get("residence"):
                j["eligibility"] = EL.eligibility(j, cfg["person"])["verdict"]
            jobs[jid] = j
    return list(jobs.values())


def company_key(name):
    return job_id(name, "x").split("/")[0]


# ------------------------------------------------------------------ employers
def employers(ws, cfg, days=90, today=None):
    rows = collections.defaultdict(lambda: {"eligible": 0, "relevant": 0, "titles": set(), "sources": set(), "first": None, "last": None, "names": collections.Counter()})
    for j in load_results(ws, cfg, days, today):
        if not j.get("company", "").strip():
            continue
        r = rows[company_key(j["company"])]
        r["names"][j["company"]] += 1
        r["relevant"] += 1
        if j.get("eligibility") in ("eligible", "likely") and not any(NOT_HIRING_HERE.search(x) for x in j.get("reasons", [])):
            r["eligible"] += 1
            r["titles"].add(j["title"])
            r["sources"].update(j.get("sources") or [j.get("source")])
            r["first"] = min(filter(None, [r["first"], j["first_seen"]]))
            r["last"] = max(filter(None, [r["last"], j["last_seen"]]))
    out = [dict(company=r["names"].most_common(1)[0][0], key=k, eligible=r["eligible"], relevant=r["relevant"], titles=sorted(r["titles"]),
                sources=sorted(s for s in r["sources"] if s), first=r["first"], last=r["last"]) for k, r in rows.items() if r["eligible"]]
    out.sort(key=lambda x: x["last"] or "", reverse=True)  # most recent first among equals
    return sorted(out, key=lambda x: -x["eligible"])


def tracked_slugs(cfg):
    return {s.lower() for slugs in cfg.get("atsBoards", {}).values() for s in slugs}


def suggest_ats(cfg, rows, limit=15):
    import verify_company as V
    have, out = tracked_slugs(cfg), []
    for r in rows[:limit]:
        if any(s in have for s in V.slugs(r["company"])):
            continue
        hit = V.ats_board(r["company"])  # "kind/slug (n jobs)"
        if hit:
            kind, slug = hit.split(" ")[0].split("/", 1)
            out.append({"company": r["company"], "kind": kind, "slug": slug, "board": hit})
    return out


def add_ats(ws, found):
    """Write slugs into filters.md -> atsBoards (rewrites the JSON block; the rest of the file is kept)."""
    path = os.path.join(ws, "search", "filters.md")
    md = open(path, encoding="utf-8").read()
    m = re.search(r"```json\s*(\{.*?\})\s*```", md, re.S)
    cfg = json.loads(m.group(1))
    boards = cfg.setdefault("atsBoards", {})
    for f in found:
        lst = boards.setdefault(f["kind"], [])
        if f["slug"] not in lst:
            lst.append(f["slug"])
    new = md[:m.start(1)] + json.dumps(cfg, indent=2, ensure_ascii=False) + md[m.end(1):]
    write_atomic(path, new)
    return boards


# ------------------------------------------------------------------ companies
def companies(ws, only=None, show_all=False):
    rows = Log(ws).load()
    by_job = collections.defaultdict(list)
    for r in rows:
        by_job[r["job"]].append(r)
    comp = collections.defaultdict(lambda: {"names": collections.Counter(), "applied": 0, "replied": 0, "days": [], "ghosted": 0, "rejected": 0,
                                            "offers": 0, "formats": collections.Counter(), "reposts": set(), "checkins": [], "postings": []})
    for jid, evs in by_job.items():
        c = comp[jid.split("/")[0]]
        for e in evs:
            c["names"][e.get("company") or jid] += 1
        if any(e["event"] == "filter" and "repost" in (e.get("reason") or []) for e in evs):
            c["reposts"].add(jid)
        st = [e for e in evs if e["event"] == "stage"]
        sub = sorted(e["date"] for e in evs if (e["event"] == "stage" and e["value"] == "submitted") or (e["event"] == "decision" and e["value"] == "applied"))
        if not sub:
            continue
        c["applied"] += 1
        replies = sorted(e["date"] for e in st if e["value"] in REPLY)
        if replies:
            c["replied"] += 1
            c["days"].append((dt.date.fromisoformat(replies[0]) - dt.date.fromisoformat(sub[0])).days)
        vals = {e["value"] for e in st}
        c["ghosted"] += "ghosted" in vals
        c["rejected"] += "rejected" in vals
        c["offers"] += bool(vals & {"offer", "hired"})
        for e in st:
            d = e.get("data") or {}
            if d.get("format"):
                c["formats"][d["format"] + (f" ({d['vendor']})" if d.get("vendor") else "")] += 1
        c["checkins"] += [e.get("data") or {} for e in evs if e["event"] == "checkin"]
        c["postings"] += [e["posting"] for e in evs if e.get("posting")]
    out = []
    for k, c in comp.items():
        name = c["names"].most_common(1)[0][0]
        if only and company_key(only) != k:
            continue
        if not only and not c["applied"] and not (show_all and c["reposts"]):
            continue
        out.append(dict(company=name, applied=c["applied"], replied=c["replied"], reply_rate=rate(c["replied"], c["applied"]) if c["applied"] else "-",
                        median_days_to_reply=statistics.median(c["days"]) if c["days"] else None, ghosted=c["ghosted"], rejected=c["rejected"],
                        offers=c["offers"], formats=dict(c["formats"]), reposts=len(c["reposts"]), checkins=c["checkins"], postings=c["postings"]))
    return sorted(out, key=lambda x: (-x["applied"], x["company"]))


# ------------------------------------------------------------------ skills
LANG_CONTEXT = re.compile(r"python|java\b|rust|c\+\+|c#|kotlin|typescript|javascript|scala|ruby|php|elixir|swift|node|sql|"
                          r"matlab|julia|sas\b|stata|pandas|statistic|tidyverse|ggplot|shiny|programming|language", re.I)


class InContext:
    """Case-sensitive match of a short language name, accepted only near other languages/tools.
    Avoids "R$ 20.000", "R&D", "go live", "go-to-market", "ready to go"."""

    def __init__(self, pattern, alias=None, window=40):
        self.rx, self.alias, self.window = re.compile(pattern), re.compile(alias, re.I) if alias else None, window

    def search(self, text):
        if self.alias and self.alias.search(text):
            return True
        for m in self.rx.finditer(text):
            context = text[max(0, m.start() - self.window):m.start()] + " " + text[m.end():m.end() + self.window]
            if LANG_CONTEXT.search(context):
                return True
        return False


SPECIAL = {
    "go": InContext(r"(?<![\w-])Go(?![\w-]|\s+(?:live|to|ahead|beyond|back)\b)", alias=r"\bgolang\b|\bgo (?:lang|programming)\b"),
    "r": InContext(r"(?<![\w$&-])R(?![\w$&\-.]|\s*\$|\s*&)", alias=r"\bR (?:language|programming|studio)\b|\bRStudio\b|\btidyverse\b"),
}


def term_re(t):
    t = t.lower()
    return SPECIAL.get(t) or re.compile(r"(?<![a-z0-9+#])" + re.escape(t) + r"(?![a-z0-9+#])", re.I)


def profile_terms(ws):
    """(have_text, do_not_claim_text) from curriculum/profile.md."""
    p = os.path.join(ws, "curriculum", "profile.md")
    if not os.path.exists(p):
        return "", ""
    md = open(p, encoding="utf-8").read()
    m = re.search(r"^#+\s*do not claim.*?$(.*?)(?=^#+\s|\Z)", md, re.M | re.S | re.I)
    if not m:
        return md, ""
    return md[:m.start()] + md[m.end():], m.group(1)


def skills(ws, cfg, top=25):
    jobs = load_results(ws, cfg)
    vocab = sorted({t.lower() for ts in VOCAB.values() for t in ts} | {t.lower() for t in cfg["roles"]["textKeywords"] + cfg["roles"]["titleKeywords"]}
                   | {t.lower() for t in (cfg.get("skills") or {}).get("extra", [])} | {k.lower() for k in cfg["fit"] if re.fullmatch(r"[\w .+#-]+", k)})
    have, dnc = profile_terms(ws)
    texts = [(j["title"] + " " + j.get("text", ""), gross(j)) for j in jobs]
    n = len(texts)
    out = []
    for t in vocab:
        rx = term_re(t)
        with_pay, without_pay, hits = [], [], 0
        for txt, g in texts:
            if rx.search(txt):
                hits += 1
                if g:
                    with_pay.append(g)
            elif g:
                without_pay.append(g)
        if not hits:
            continue
        status = "gap (listed in Do NOT claim)" if dnc and rx.search(dnc) else "have" if rx.search(have) else "gap"
        pay = None
        if len(with_pay) >= MIN_N and len(without_pay) >= MIN_N:
            pay = round(statistics.median(with_pay) / statistics.median(without_pay) - 1, 2)
        out.append(dict(skill=t, jobs=hits, share=hits / n if n else 0, status=status, pay_vs_without=pay, n_pay=(len(with_pay), len(without_pay))))
    out.sort(key=lambda x: -x["jobs"])
    return {"jobs": n, "gaps": [x for x in out if x["status"] != "have"][:top], "strengths": [x for x in out if x["status"] == "have"][:top],
            "pay_linked": sorted([x for x in out if x["pay_vs_without"] is not None], key=lambda x: -x["pay_vs_without"])[:10]}


# ------------------------------------------------------------------ weekly
def weekly(ws, days=7, today=None):
    today = today or dt.date.today()
    rows = Log(ws).load()
    start, prev = today - dt.timedelta(days=days), today - dt.timedelta(days=2 * days)

    def in_win(r, a, b):
        return a < dt.date.fromisoformat(r["date"]) <= b

    def summary(a, b):
        w = [r for r in rows if in_win(r, a, b)]
        return {"scans": len({r["date"] for r in w if r["event"] == "filter"}),
                "kept": len({r["job"] for r in w if r["event"] == "filter" and r["value"] == "keep"}),
                "applied": len({r["job"] for r in w if (r["event"] == "decision" and r["value"] == "applied") or (r["event"] == "stage" and r["value"] == "submitted")}),
                "skipped": len({r["job"] for r in w if r["event"] == "decision" and r["value"] == "skipped"}),
                "replies": len({r["job"] for r in w if r["event"] == "stage" and r["value"] in REPLY}),
                "interviews": len({r["job"] for r in w if r["event"] == "stage" and r["value"] == "interview"})}

    by_job = collections.defaultdict(list)
    for r in rows:
        if r["event"] in ("stage", "decision"):
            by_job[r["job"]].append(r)
    channels = collections.defaultdict(lambda: [0, 0])
    ghost, follow = [], []
    for jid, evs in by_job.items():
        sub = sorted([e for e in evs if (e["event"] == "stage" and e["value"] == "submitted") or (e["event"] == "decision" and e["value"] == "applied")],
                     key=lambda e: e["date"])
        if not sub:
            continue
        ch = next(((e.get("data") or {}).get("channel") for e in evs if (e.get("data") or {}).get("channel")), "unknown")
        vals = {e["value"] for e in evs if e["event"] == "stage"}
        channels[ch][0] += 1
        channels[ch][1] += bool(vals & REPLY)
        age = (today - dt.date.fromisoformat(sub[0]["date"])).days
        name = sub[0].get("company") or jid
        if not vals & (REPLY | ENDED):
            if age >= 21:
                ghost.append((name, age))
            elif age >= 5:
                follow.append((name, age))
    cur, before = summary(start, today), summary(prev, start)
    tips = []
    for ch, (a, rp) in channels.items():
        if a >= MIN_N and rp == 0:
            tips.append(f"{a} applications via {ch} and no reply: spend less time on that channel")
    kept_open = len({r["job"] for r in rows if r["event"] == "filter" and r["value"] == "keep" and in_win(r, start, today)} - set(by_job))
    if kept_open and not cur["applied"]:
        tips.append(f"{kept_open} kept jobs this week with no decision: apply or skip (and log why)")
    if ghost:
        tips.append("no reply for 3+ weeks: " + ", ".join(f"{n} ({a}d)" for n, a in ghost) + ". Follow up once or close as ghosted")
    pending = due(ws, today)["checkins"]
    if pending:
        tips.insert(0, "retention check-in due: " + ", ".join(f"{n} ({lab})" for n, lab, _ in pending))
    if follow:
        tips.append("follow-up due (5-20 days, no reply): " + ", ".join(f"{n} ({a}d)" for n, a in follow) + ". One short polite message each")
    if not tips:
        total = sum(a for a, _ in channels.values())
        tips.append("too few applications to compare channels yet" if total < 10 else "no warning signs this week")
    return {"window": f"{start + dt.timedelta(days=1)}..{today}", "this": cur, "previous": before,
            "channels": {c: {"applied": a, "replied": rp, "reply_rate": rate(rp, a)} for c, (a, rp) in channels.items()},
            "follow_up": follow, "ghost_risk": ghost, "suggestion": tips[0], "other_tips": tips[1:]}


# ------------------------------------------------------------------ due
CHECKINS = [("30d", 30), ("90d", 90), ("180d", 180), ("365d", 365)]


def due(ws, today=None):
    """Follow-ups, ghost risk, upcoming interviews and retention check-ins that are due."""
    today = today or dt.date.today()
    rows = Log(ws).load()
    by_job = collections.defaultdict(list)
    for r in rows:
        by_job[r["job"]].append(r)
    out = {"follow_up": [], "ghost_risk": [], "interviews": [], "checkins": []}
    for jid, evs in by_job.items():
        name = next((e.get("company") for e in evs if e.get("company")), jid)
        st = {e["value"]: e["date"] for e in sorted(evs, key=lambda e: e["date"]) if e["event"] == "stage"}
        sub = min([e["date"] for e in evs if (e["event"] == "stage" and e["value"] == "submitted") or (e["event"] == "decision" and e["value"] == "applied")] or [None], key=lambda x: x or "9")
        if sub and not set(st) & (REPLY | ENDED):
            age = (today - dt.date.fromisoformat(sub)).days
            nudged = st.get("followed_up")
            if age >= 21:
                out["ghost_risk"].append((name, age))
            elif age >= 5 and not (nudged and (today - dt.date.fromisoformat(nudged)).days < 7):
                out["follow_up"].append((name, age))
        for e in evs:
            when = (e.get("data") or {}).get("scheduled")
            if e["event"] == "stage" and when and re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(when)):
                d = (dt.date.fromisoformat(when) - today).days
                if 0 <= d <= 7 and not set(st) & ENDED:
                    out["interviews"].append((name, when))
        if "hired" in st:
            done = {e["value"] for e in evs if e["event"] == "checkin"}
            if "left" not in done:
                hired = dt.date.fromisoformat(st["hired"])
                for label, days in CHECKINS:
                    if label not in done and (today - hired).days >= days:
                        out["checkins"].append((name, label, str(hired + dt.timedelta(days=days))))
                        break  # one pending check-in per job: the earliest
    out["interviews"] = sorted(set(out["interviews"]), key=lambda x: x[1])
    return out


# ------------------------------------------------------------------ cli
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("employers")
    e.add_argument("--days", type=int, default=90)
    e.add_argument("--suggest-ats", action="store_true")
    e.add_argument("--add", action="store_true", help="write the found slugs into filters.md (ask the user first)")
    c = sub.add_parser("companies")
    c.add_argument("--company")
    c.add_argument("--all", action="store_true", help="also companies you never applied to (repost history)")
    s = sub.add_parser("skills")
    s.add_argument("--top", type=int, default=25)
    w = sub.add_parser("weekly")
    w.add_argument("--days", type=int, default=7)
    sub.add_parser("due")
    a = ap.parse_args()
    ws = os.path.abspath(os.path.expanduser(a.workspace))
    cfg = load_config(ws, require_queries=False)

    if a.cmd == "employers":
        rows = employers(ws, cfg, a.days)
        if not cfg["person"].get("residence"):
            print("note: set filters.md -> person.residence for eligibility-based results")
        print(f"Employers with jobs you can take (last {a.days} days): {len(rows)}")
        for r in rows[:30]:
            print(f"  {r['eligible']:3d} eligible / {r['relevant']:3d} relevant  {r['company'][:30]:30} last {r['last']}  {'; '.join(r['titles'][:3])[:80]}")
        if a.suggest_ats or a.add:
            found = suggest_ats(cfg, rows)
            print("\nJob boards found for companies you don't watch yet:" if found else "\nNo new job boards found.")
            for f in found:
                print(f"  {f['company']}: {f['board']}  (found by name: open it and check it is the same company)")
            if found and a.add:
                print("added to filters.md -> atsBoards:", json.dumps(add_ats(ws, found)))
            elif found:
                print("To watch them, add to filters.md -> atsBoards (or re-run with --add after the user agrees).")
    elif a.cmd == "companies":
        rows = companies(ws, a.company, a.all)
        print(f"Companies in your log: {len(rows)} (rates need ≥ {MIN_N} applications; below that, counts)")
        for r in rows:
            d = f"{r['median_days_to_reply']}d" if r["median_days_to_reply"] is not None else "-"
            print(f"  {r['company'][:28]:28} applied {r['applied']} | replied {r['reply_rate']} | median reply {d} | ghosted {r['ghosted']} | "
                  f"rejected {r['rejected']} | offers {r['offers']} | reposted jobs {r['reposts']}")
            if r["formats"]:
                print("       interviews:", ", ".join(f"{k} ×{v}" for k, v in r["formats"].items()))
            for ck in r["checkins"]:
                print("       check-in:", json.dumps(ck, ensure_ascii=False))
            for p in r["postings"][:1]:
                print("       posting saved:", p)
    elif a.cmd == "skills":
        r = skills(ws, cfg, a.top)
        print(f"Skills across {r['jobs']} relevant jobs (all scans). 'have' = found in curriculum/profile.md outside 'Do NOT claim'.")
        print("\nMost requested skills you don't show:")
        for x in r["gaps"]:
            print(f"  {x['skill']:24} {x['jobs']:4d} jobs ({x['share']:.0%})  {x['status']}")
        print("\nMost requested skills you have:")
        for x in r["strengths"][:15]:
            print(f"  {x['skill']:24} {x['jobs']:4d} jobs ({x['share']:.0%})")
        print("\nPay of jobs with vs without the skill (median gross; only where both groups have ≥ %d jobs with pay):" % MIN_N)
        for x in r["pay_linked"] or []:
            print(f"  {x['skill']:24} {x['pay_vs_without']:+.0%}  (n {x['n_pay'][0]} vs {x['n_pay'][1]})  {x['status']}")
        if not r["pay_linked"]:
            print("  too few jobs with listed pay yet")
    elif a.cmd == "due":
        r = due(ws)
        if not any(r.values()):
            print("Nothing due today.")
        for n, when in r["interviews"]:
            print(f"interview: {n} on {when}: offer prep")
        for n, label, since in r["checkins"]:
            print(f"retention check-in {label} due for {n} (since {since}): satisfaction 1-5, did the job match the posting 1-5, would you stay? -> outcomes.py event --event checkin --value {label}")
        for n, age in r["follow_up"]:
            print(f"follow-up: {n}, applied {age} days ago, no reply")
        for n, age in r["ghost_risk"]:
            print(f"ghost risk: {n}, {age} days without reply: follow up once or close as ghosted")
    else:
        r = weekly(ws, a.days)
        t, p = r["this"], r["previous"]
        print(f"Week {r['window']}  (previous window in brackets)")
        for k in ("scans", "kept", "applied", "skipped", "replies", "interviews"):
            print(f"  {k:10} {t[k]:3d}  [{p[k]}]")
        print(f"  by channel (all time; % only from {MIN_N} applications):", ", ".join(f"{c}: {v['reply_rate']} replied" for c, v in r["channels"].items()) or "-")
        if r["follow_up"]:
            print("  follow-up due (5-20 days, no reply):", ", ".join(f"{n} ({a}d)" for n, a in r["follow_up"]))
        print("\nSuggestion:", r["suggestion"])
        for tip in r["other_tips"]:
            print("  also:", tip)


if __name__ == "__main__":
    main()
