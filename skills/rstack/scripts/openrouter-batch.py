#!/usr/bin/env python3
"""openrouter-batch.py: run one prompt template over many items through the OpenRouter API, with a spend threshold.

For API tasks that are too many or too repetitive for an agent: classifying or labelling records, extracting
fields into JSON, summarising many documents, generating test fixtures or variants, translating strings,
grading outputs against a rubric (model-as-judge), comparing models on the same inputs.

Usage:
  openrouter-batch.py --model <vendor/model> --template prompt.txt --in items.jsonl --out results.jsonl
                      [--json] [--concurrency 4] [--max-items N] [--max-cost-usd 2.00] [--keychain-service openrouter-api]

- items.jsonl: one JSON object per line, each with an "id" and the fields the template uses ({field} placeholders).
- results.jsonl: one line per item: {"id", "model", "output", "cost_usd", "error"}. A rerun skips successful ids.
  Failed items can run again.
- --json asks the model for a JSON object (response_format json_object) and checks the output parses.
- --max-cost-usd stops starting new items once the reported spend reaches the threshold (default 2.00). Requests already in flight
  can take spend over that amount. Set a limit on the OpenRouter key too.
Never put secrets, credentials or personal data you may not share in the items or the template.
"""
import argparse, json, os, subprocess, sys, threading, time, urllib.error, urllib.request
from concurrent.futures import ThreadPoolExecutor


def api_key(service):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    try:
        return subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        sys.exit("STOP: no OPENROUTER_API_KEY and no keychain item '%s'" % service)


def call(key, model, prompt, want_json):
    body = {"model": model, "messages": [{"role": "user", "content": prompt}], "usage": {"include": True}}
    if want_json:
        body["response_format"] = {"type": "json_object"}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": "Bearer " + key, "Content-Type": "application/json",
                                          "X-Title": "rstack"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=300) as resp:
                data = json.load(resp)
            out = data["choices"][0]["message"]["content"]
            if want_json:
                json.loads(out)  # raises if the model did not return valid JSON
            return out, float(data.get("usage", {}).get("cost") or 0.0), None
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < 3:
                wait = float(e.headers.get("Retry-After") or 2 ** (attempt + 1))
                time.sleep(min(wait, 60))
                continue
            return None, 0.0, "HTTP %d" % e.code
        except Exception as e:  # network error, bad JSON, missing field
            if attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            return None, 0.0, type(e).__name__ + ": " + str(e)[:200]
    return None, 0.0, "gave up"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--concurrency", type=int, default=4)
    ap.add_argument("--max-items", type=int, default=0)
    ap.add_argument("--max-cost-usd", type=float, default=2.0)
    ap.add_argument("--keychain-service", default="openrouter-api")
    a = ap.parse_args()

    template = open(a.template, encoding="utf-8").read()
    items = [json.loads(line) for line in open(a.inp, encoding="utf-8") if line.strip()]
    done = set()
    if os.path.exists(a.out):
        for line in open(a.out, encoding="utf-8"):
            try:
                row = json.loads(line)
                if not row.get("error"):
                    done.add(row["id"])
            except Exception:
                pass
    todo = [it for it in items if it.get("id") not in done]
    if a.max_items:
        todo = todo[: a.max_items]
    key = api_key(a.keychain_service)
    lock = threading.Lock()
    spent = [0.0]
    stopped = [False]

    def work(item):
        with lock:
            if spent[0] >= a.max_cost_usd:
                stopped[0] = True
                return
        try:
            prompt = template.format(**item)
        except KeyError as e:
            out, cost, err = None, 0.0, "template field missing: %s" % e
        else:
            out, cost, err = call(key, a.model, prompt, a.json)
        with lock:
            spent[0] += cost
            with open(a.out, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": item.get("id"), "model": a.model, "output": out,
                                     "cost_usd": round(cost, 6), "error": err}) + "\n")

    with ThreadPoolExecutor(max_workers=max(1, a.concurrency)) as pool:
        list(pool.map(work, todo))
    print("openrouter-batch: model=%s items=%d skipped_done=%d spent_usd=%.4f%s" % (
        a.model, len(todo), len(done), spent[0], " (STOPPED at the cost cap)" if stopped[0] else ""))


if __name__ == "__main__":
    main()
