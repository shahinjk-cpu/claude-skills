#!/usr/bin/env python3
"""openrouter-ask.py: send a brief plus a few named files to any model on the OpenRouter API and save its answer.

For read-only jobs that need no shell: reviews, plan-panel reviews, cause reads over pasted logs, summaries.
The model gets only the text you pass; it cannot run commands or touch the repository.

Usage:
  openrouter-ask.py --model <vendor/model> --brief brief.md [--file path ...] --out answer.md [--max-chars 400000]

Key: OPENROUTER_API_KEY in the environment, or the macOS keychain item named by --keychain-service
(default "openrouter-api"), read with `security find-generic-password -s <service> -w`. Never put the key in a file.

Screens attachment paths for common secret names and stops when the total text exceeds --max-chars.
Check the brief and all attachments for sensitive content before sending.
"""
import argparse, json, os, re, subprocess, sys, urllib.request

SECRET_PATTERNS = [
    r"(^|/)\.env(\..*)?$", r"credentials", r"(^|/)\.aws/", r"(^|/)\.ssh/", r"id_(rsa|ed25519|ecdsa)",
    r"\.(pem|key|p12|pfx|keystore|jks)$", r"\.tfstate(\.backup)?$", r"\.tfplan$", r"(^|/)\.netrc$",
    r"\.modal\.toml$", r"(^|/)\.npmrc$", r"(^|/)\.pypirc$", r"secret", r"token",
]


def api_key(service):
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if key:
        return key
    try:
        return subprocess.run(["security", "find-generic-password", "-s", service, "-w"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        sys.exit("STOP: no OPENROUTER_API_KEY and no keychain item '%s'" % service)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True, help="OpenRouter model id, e.g. moonshotai/kimi-k2")
    ap.add_argument("--brief", required=True)
    ap.add_argument("--file", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-chars", type=int, default=400_000)
    ap.add_argument("--keychain-service", default="openrouter-api")
    a = ap.parse_args()

    parts = [open(a.brief, encoding="utf-8").read()]
    for path in a.file:
        norm = os.path.realpath(path)
        if any(re.search(p, norm, re.I) for p in SECRET_PATTERNS):
            sys.exit("STOP: refusing %s (looks like a secret or credential file)" % path)
        with open(norm, encoding="utf-8", errors="replace") as fh:
            parts.append("\n\n===== FILE: %s =====\n%s" % (path, fh.read()))
    text = "".join(parts)
    if len(text) > a.max_chars:
        sys.exit("STOP: %d characters is over --max-chars %d; send fewer or smaller files" % (len(text), a.max_chars))

    body = json.dumps({"model": a.model, "messages": [{"role": "user", "content": text}]}).encode()
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=body, headers={
        "Authorization": "Bearer " + api_key(a.keychain_service),
        "Content-Type": "application/json",
        "X-Title": "rstack",
    })
    with urllib.request.urlopen(req, timeout=600) as resp:
        data = json.load(resp)
    answer = data["choices"][0]["message"]["content"]
    with open(a.out, "w", encoding="utf-8") as fh:
        fh.write(answer)
    usage = data.get("usage", {})
    print("openrouter-ask: model=%s out=%s prompt_tokens=%s completion_tokens=%s" % (
        a.model, a.out, usage.get("prompt_tokens"), usage.get("completion_tokens")))


if __name__ == "__main__":
    main()
