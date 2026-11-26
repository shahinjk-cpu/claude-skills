#!/usr/bin/env python3
"""Stand-in for the agy, codex and grok CLIs in tests.

Behaviour is set per CLI by the environment variable STUB_<NAME>_MODE:
  ok (default)  reply "CORUN 5" plus the prompt length
  noout         (codex) exit 0 without writing the -o file
  echo          reply with the prompt text itself
  fail          exit 1 with an error on stderr
  perm          print a permission refusal on stderr and exit 0 (Grok's headless behaviour)
  permout       (agy) print a refusal on stderr and a partial answer on stdout
  nosandbox     (grok) print Grok's "sandbox could not be applied" warning, then reply
  empty         exit 0 with no output
  slow          sleep 30 seconds, then reply
STUB_<NAME>_VERSION sets the --version output. Every call's argv, working folder, environment
names and the grok sandbox profile or agy settings file are appended, as JSON, to the file named by STUB_LOG.
Settings come from stub_env.json beside the stub, since corun filters the environment.
"""
import contextlib
import json
import re
import os
import sys
import time

name = os.path.basename(sys.argv[0])
# corun passes partners a filtered environment, so the tests put the stub settings in
# stub_env.json beside the stub.
settings = {}
with contextlib.suppress(OSError, ValueError):
    with open(os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "stub_env.json")) as f:
        settings = json.load(f)
mode = settings.get("STUB_%s_MODE" % name.upper(), "ok")
log = settings.get("STUB_LOG")
profile = None
if name == "grok" and os.path.isfile(os.path.join(os.getcwd(), ".grok", "sandbox.toml")):
    with open(os.path.join(os.getcwd(), ".grok", "sandbox.toml")) as f:
        profile = f.read()
if name == "agy" and "--settings" in sys.argv:
    with open(sys.argv[sys.argv.index("--settings") + 1]) as f:
        profile = f.read()
if log:
    with open(log, "a") as f:
        f.write(json.dumps({"cli": name, "argv": sys.argv[1:], "cwd": os.getcwd(),
                            "env": sorted(os.environ), "tmpdir": os.environ.get("TMPDIR"),
                            "profile": profile}) + "\n")

if sys.argv[1:] == ["--version"]:
    print(settings.get("STUB_%s_VERSION" % name.upper(), "%s 1.0" % name))
    sys.exit(0)

args = sys.argv[1:]
if args and args[-1] == "-":
    prompt = sys.stdin.read()
elif "--prompt-file" in args:
    with open(args[args.index("--prompt-file") + 1]) as f:
        prompt = f.read()
else:
    prompt = next((a[3:] for a in args if a.startswith("-p=")), args[-1] if args else "")
    task = re.match(r"Read the task in (\S+) and carry it out", prompt)
    if task:
        with open(task.group(1)) as f:
            prompt = f.read()
# corun probes with a fixed prompt; answer it as a model would.
probe = "Reply with exactly the word CORUN" in prompt
if log:
    with open(log, "a") as f:
        f.write(json.dumps({"cli": name, "prompt": prompt}) + "\n")
reply = "CORUN 5" if probe else "CORUN 5 from %s (prompt %d chars)" % (name, len(prompt))
if mode == "echo":
    reply = prompt

if mode == "fail":
    print("stub failure", file=sys.stderr)
    sys.exit(1)
if mode == "perm":
    print("permission required: Execute `x` was not run, as a headless run cannot ask for approval",
          file=sys.stderr)
    sys.exit(0)
if mode == "permout":
    print("a tool required the read_file permission that headless mode cannot prompt for, "
          "so it was auto-denied.", file=sys.stderr)
    print("partial answer")
    sys.exit(0)
if mode == "nosandbox":
    print("warning: sandbox could not be applied: test", file=sys.stderr)
if mode == "empty":
    sys.exit(0)
if mode == "slow":
    time.sleep(30)

if mode == "noout":
    print("codex progress noise")
    sys.exit(0)
if name == "codex" and "-o" in args:
    with open(args[args.index("-o") + 1], "w") as f:
        f.write(reply + "\n")
    print("codex progress noise")
else:
    print(reply)
