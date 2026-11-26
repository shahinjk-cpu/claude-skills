#!/usr/bin/env python3
"""Build one list of everyone you interacted with: texts, email, calendar.

Inputs (all in --dir; only people.json is required):
  people.json      from find_people.py (texts)
  email_sent.txt   one address per line: people you emailed
  calendar.json    [{name, email, last, count}] meeting guests
  drafts.json      optional {"<name, phone or email>": {"draft": "...", "notes": "..."}}
  notes.json       optional {"<name, phone or email>": {"priority": "...", "notes": "..."}}

Writes people.csv, sorted high > medium > low priority. Matches emails to names
and phone numbers through your macOS Contacts. Reads everything read-only and
sends nothing: the list is for you to work through yourself.
"""
import argparse, csv, glob, json, os, re, sqlite3
from collections import Counter

AB = os.path.expanduser("~/Library/Application Support/AddressBook")
SKIP = re.compile(r"^(no-?reply|noreply|do-?not-?reply|tracker|info|hello|support|ai|business|team|admin|"
                  r"billing|notifications?|member|receipts?|orders?|news|newsletter)@|unsubscribe", re.I)
RANK = {"high": 0, "medium": 1, "low": 2}


def contacts_by_email():
    out = {}
    dbs = glob.glob(f"{AB}/AddressBook-v22.abcddb") + glob.glob(f"{AB}/Sources/*/AddressBook-v22.abcddb")
    for db in dbs:
        try:
            con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
            names = {pk: " ".join(x for x in (f, l) if x) or o for pk, f, l, o in
                     con.execute("select Z_PK, ZFIRSTNAME, ZLASTNAME, ZORGANIZATION from ZABCDRECORD")}
            phones = {}
            for owner, num in con.execute("select ZOWNER, ZFULLNUMBER from ZABCDPHONENUMBER"):
                if num:
                    phones.setdefault(owner, num)
            for owner, addr in con.execute("select ZOWNER, ZADDRESS from ZABCDEMAILADDRESS"):
                if addr:
                    out.setdefault(addr.lower().strip(), {"name": names.get(owner), "phone": phones.get(owner)})
            con.close()
        except sqlite3.Error:
            continue
    return out


def load(path, default):
    return json.load(open(path)) if os.path.exists(path) else default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True)
    ap.add_argument("--self", nargs="*", default=[], help="your own addresses to drop")
    ap.add_argument("--high", type=int, default=25, help="how many people get high priority")
    a = ap.parse_args()
    d = os.path.expanduser(a.dir)
    me = {s.lower() for s in a.self}
    cbe = contacts_by_email()

    rows = {}

    def key(name, phone, email):
        return ("n", name.lower()) if name else ("p", phone) if phone else ("e", email)

    for p in load(f"{d}/people.json", {"people": []})["people"]:
        phone = next((h for h in p["all_handles"] if "@" not in h), "")
        email = next((h for h in p["all_handles"] if "@" in h), "")
        rows[key(p["name"], phone, email)] = {
            "name": p["name"] or "", "phone": phone, "email": email, "sources": {"text"},
            "texts": p["total"], "two_way": min(p["sent"], p["received"]), "score": p["score"],
            "last_contact": p["last_message"], "meetings": 0, "draft": "", "notes": ""}

    def add(email, name, source, last="", count=0):
        email = email.lower().strip()
        if not email or email in me or SKIP.search(email):
            return
        c = cbe.get(email, {})
        name = c.get("name") or name or ""
        r = rows.setdefault(key(name, None, email) if name else ("e", email), {
            "name": name, "phone": c.get("phone") or "", "email": email, "sources": set(), "texts": 0,
            "two_way": 0, "score": 0, "last_contact": "", "meetings": 0, "draft": "", "notes": ""})
        r["sources"].add(source)
        r["email"] = r["email"] or email
        r["phone"] = r["phone"] or c.get("phone") or ""
        r["last_contact"] = max(r["last_contact"], last)
        r["meetings"] += count

    if os.path.exists(f"{d}/email_sent.txt"):
        for line in sorted(set(open(f"{d}/email_sent.txt"))):
            add(line, "", "email")
    for c in load(f"{d}/calendar.json", []):
        add(c["email"], c.get("name", ""), "calendar", c.get("last", ""), c.get("count", 1))

    # Fold email-only rows into a texted person when the address spells their name
    # (jdoe@ or jane.doe@ for "Jane Doe"; jane@ only if there is exactly one texted Jane).
    texted = [r for r in rows.values() if "text" in r["sources"] and len(r["name"].split()) >= 2]
    firsts = Counter(r["name"].split()[0].lower() for r in texted)
    for k in [k for k, r in rows.items() if "text" not in r["sources"]]:
        r = rows[k]
        local, _, domain = r["email"].partition("@")
        local = re.sub(r"[^a-z]", "", local)
        hit = None
        for t in texted:
            parts = re.sub(r"[^a-z ]", "", t["name"].lower()).split()
            if len(parts) < 2 or len(parts[-1]) < 3:
                continue
            first, last = parts[0], parts[-1]
            if (last in local and (first in local or local.startswith(first[0]))) or \
               (local == first and last in domain) or \
               (not r["name"] and local == first and firsts[first] == 1):
                hit = t
                break
        if hit:
            hit["sources"] |= r["sources"]
            hit["email"] = hit["email"] or r["email"]
            hit["last_contact"] = max(hit["last_contact"], r["last_contact"])
            hit["meetings"] += r["meetings"]
            del rows[k]

    def lookup(table):
        idx = {}
        for k, v in table.items():
            idx[k.lower().strip()] = v
            digits = re.sub(r"\D", "", k)
            if len(digits) >= 10:
                idx[digits[-10:]] = v
        return idx

    def find(idx, r):
        ids = [r["name"].lower(), r["email"].lower(), re.sub(r"\D", "", r["phone"])[-10:]]
        return next((idx[i] for i in ids if i and i in idx), None)

    overrides = lookup(load(f"{d}/notes.json", {}))
    drafts = lookup(load(f"{d}/drafts.json", {}))

    # Priority: rows you set in notes.json keep that priority. Of the rest, the top
    # --high by texting score are high; anyone with a real back-and-forth, a meeting,
    # or more than one channel is medium; everyone else is low.
    ranked = sorted(rows.values(), key=lambda r: -r["score"])
    slots = a.high
    for r in ranked:
        o = find(overrides, r) or {}
        r["notes"] = o.get("notes", "")
        if o.get("priority"):
            r["priority"] = o["priority"]
        elif slots and r["score"] > 0:
            r["priority"] = "high"
            slots -= 1
        elif r["two_way"] >= 5 or r["meetings"] or len(r["sources"]) > 1:
            r["priority"] = "medium"
        else:
            r["priority"] = "low"

    used = 0
    for r in ranked:
        dr = find(drafts, r)
        if dr:
            r["draft"] = dr.get("draft", "")
            r["notes"] = dr.get("notes") or r["notes"]
            used += 1

    for r in ranked:
        r["sources"] = "+".join(sorted(r["sources"]))
    ranked.sort(key=lambda r: (RANK.get(r["priority"], 3), -r["score"], -r["meetings"], r["name"] or r["email"]))
    cols = ["done", "priority", "name", "phone", "email", "sources", "texts", "last_contact", "draft", "notes"]
    path = f"{d}/people.csv"
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(ranked)
    os.chmod(path, 0o600)
    print(f"{len(ranked)} people -> {path}")
    print("priority:", dict(Counter(r["priority"] for r in ranked)))
    print("sources:", dict(Counter(r["sources"] for r in ranked)))
    print("drafts filled:", used, "| with a phone:", sum(bool(r["phone"]) for r in ranked))


if __name__ == "__main__":
    main()
