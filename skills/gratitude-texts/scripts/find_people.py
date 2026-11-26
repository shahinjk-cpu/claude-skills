#!/usr/bin/env python3
"""Find the people you actually talk to, from your local iMessage history.

Reads ~/Library/Messages/chat.db and your macOS Contacts databases, read-only.
Nothing leaves your machine. Writes people.json to --out.

Keeps every 1:1 thread where both sides wrote inside the lookback window
(default: the past year, at least 1 message each way). Group chats,
verification codes, and businesses that never get replies fall out on their own.

Usage:
  python3 find_people.py --out ~/gratitude-texts/$(date +%Y)
  python3 find_people.py --out DIR --days 730 --min-each-way 3 --limit 200
"""
import argparse
import glob
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone

HOME = os.path.expanduser("~")
CHAT_DB = os.path.join(HOME, "Library/Messages/chat.db")
AB_ROOT = os.path.join(HOME, "Library/Application Support/AddressBook")
APPLE_EPOCH = datetime(2001, 1, 1, tzinfo=timezone.utc)

FDA_HELP = """
Can't read your Messages or Contacts database: macOS is blocking access.

Fix (one time):
  System Settings > Privacy & Security > Full Disk Access
  Turn on the app you run Claude Code from (Terminal, iTerm, Claude, VS Code...).
  Then fully QUIT that app (Cmd+Q, not just close the window) and reopen it.
  macOS only applies the permission after a full restart.
"""


def open_ro(path):
    con = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    con.execute("select 1 from sqlite_master limit 1")
    return con


def apple_ts(raw):
    if not raw:
        return None
    secs = raw / 1e9 if raw > 1e11 else raw  # ns on modern macOS, s on old
    return APPLE_EPOCH + timedelta(seconds=secs)


def to_apple(dt):
    return int((dt - APPLE_EPOCH).total_seconds() * 1e9)


def decode_body(blob):
    """Pull plain text out of attributedBody (newer macOS leaves text NULL)."""
    if not blob:
        return None
    try:
        i = blob.index(b"NSString")
    except ValueError:
        return None
    b = blob[i + len(b"NSString") + 5:]
    if not b:
        return None
    if b[0] == 0x81:
        length, start = int.from_bytes(b[1:3], "little"), 3
    elif b[0] == 0x82:
        length, start = int.from_bytes(b[1:4], "little"), 4
    else:
        length, start = b[0], 1
    return b[start:start + length].decode("utf-8", errors="ignore") or None


def norm_handle(h):
    h = (h or "").strip().lower()
    if "@" in h:
        return h
    digits = re.sub(r"\D", "", h)
    return digits[-10:] if len(digits) >= 10 else digits


def load_contacts():
    """Map normalized phone/email -> display name across all Contacts sources."""
    names = {}
    if os.path.isdir(AB_ROOT):
        os.listdir(AB_ROOT)  # raises PermissionError without Full Disk Access
    dbs = glob.glob(os.path.join(AB_ROOT, "AddressBook-v22.abcddb"))
    dbs += glob.glob(os.path.join(AB_ROOT, "Sources/*/AddressBook-v22.abcddb"))
    for db in dbs:
        try:
            con = open_ro(db)
        except sqlite3.Error:
            continue
        people = {}
        for pk, first, last, nick, org in con.execute(
            "select Z_PK, ZFIRSTNAME, ZLASTNAME, ZNICKNAME, ZORGANIZATION from ZABCDRECORD"
        ):
            full = " ".join(x for x in (first, last) if x) or nick or org
            if full:
                people[pk] = {"name": full, "first": first or nick or full.split()[0],
                              "is_org": not (first or last) and bool(org)}
        rows = list(con.execute("select ZOWNER, ZFULLNUMBER from ZABCDPHONENUMBER"))
        rows += list(con.execute("select ZOWNER, ZADDRESS from ZABCDEMAILADDRESS"))
        for owner, val in rows:
            if owner in people and val:
                names.setdefault(norm_handle(val), people[owner])
        con.close()
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--days", type=int, default=365, help="lookback window")
    ap.add_argument("--min-each-way", type=int, default=1)
    ap.add_argument("--limit", type=int, default=0, help="0 = everyone")
    ap.add_argument("--recent", type=int, default=15, help="recent messages kept per person")
    args = ap.parse_args()

    try:
        chat = open_ro(CHAT_DB)
    except sqlite3.Error:
        sys.exit(FDA_HELP)
    try:
        contacts = load_contacts()
    except (sqlite3.Error, PermissionError):
        sys.exit(FDA_HELP)

    since = datetime.now(timezone.utc) - timedelta(days=args.days)
    q = """
    select h.id, m.is_from_me, m.date, m.text, m.attributedBody
    from chat c
    join chat_handle_join chj on chj.chat_id = c.ROWID
    join handle h on h.ROWID = chj.handle_id
    join chat_message_join cmj on cmj.chat_id = c.ROWID
    join message m on m.ROWID = cmj.message_id
    where c.ROWID in (select chat_id from chat_handle_join group by chat_id having count(*) = 1)
      and m.date > ?
      and coalesce(m.associated_message_type, 0) = 0
    order by m.date
    """
    people = defaultdict(lambda: {"handles": set(), "sent": 0, "received": 0,
                                  "last": None, "msgs": []})
    for handle, from_me, date, text, body in chat.execute(q, (to_apple(since),)):
        key_h = norm_handle(handle)
        if not key_h or ("@" not in key_h and len(key_h) < 10):
            continue  # short codes: banks, 2FA, delivery alerts
        contact = contacts.get(key_h)
        key = ("c", contact["name"]) if contact else ("h", key_h)
        p = people[key]
        p["handles"].add(handle)
        p["contact"] = contact
        p["sent" if from_me else "received"] += 1
        ts = apple_ts(date)
        p["last"] = ts
        txt = text or decode_body(body)
        if txt:
            txt = txt.replace("￼", "").strip()
            if txt:
                p["msgs"].append({"me": bool(from_me), "at": ts.date().isoformat(),
                                  "text": txt[:240]})
    chat.close()

    now = datetime.now(timezone.utc)
    out = []
    for (kind, ident), p in people.items():
        if p["sent"] < args.min_each_way or p["received"] < args.min_each_way:
            continue
        c = p.get("contact")
        if c and c["is_org"]:
            continue
        days_since = (now - p["last"]).days
        total = p["sent"] + p["received"]
        score = round(min(p["sent"], p["received"]) ** 0.5 * 10 / (1 + days_since / 90), 2)
        # Prefer a phone handle for sending; fall back to email (iMessage only)
        handles = sorted(p["handles"], key=lambda h: ("@" in h, h))
        out.append({
            "name": c["name"] if c else None,
            "first_name": c["first"] if c else None,
            "in_contacts": bool(c),
            "handle": handles[0],
            "all_handles": handles,
            "sent": p["sent"], "received": p["received"], "total": total,
            "last_message": p["last"].date().isoformat(),
            "days_since": days_since,
            "score": score,
            "recent": p["msgs"][-args.recent:],
        })
    out.sort(key=lambda x: -x["score"])
    if args.limit:
        out = out[:args.limit]

    os.makedirs(os.path.expanduser(args.out), exist_ok=True)
    path = os.path.join(os.path.expanduser(args.out), "people.json")
    with open(path, "w") as f:
        json.dump({"generated": now.isoformat(), "window_days": args.days,
                   "contacts_loaded": len(contacts), "people": out}, f, indent=1)
    os.chmod(path, 0o600)
    named = sum(1 for x in out if x["in_contacts"])
    print(f"{len(out)} people ({named} in Contacts, {len(out) - named} number-only) -> {path}")


if __name__ == "__main__":
    main()
