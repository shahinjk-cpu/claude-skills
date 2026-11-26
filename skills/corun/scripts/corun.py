#!/usr/bin/env python3
"""corun: call partner AI command-line tools for the Corun skill.

Subcommands
  check [--only P ...]       probe partners with their exact model and effort, write the roster,
                             print the declaration
  status                     print the declaration (re-checks first when the roster is stale)
  ask ROLE --prompt-file F   send a task to the first healthy partner for ROLE, falling back
                             along the role's chain; output goes to stdout
  scan DIR                   pre-publish privacy scan of DIR

Exit codes: 0 success; 2 no partner succeeded; 3 the role falls back to a Claude subagent;
4 usage or configuration error.

Python 3.9 standard library only.
"""
import argparse
import concurrent.futures
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
PROBE_PROMPT = "Reply with exactly the word CORUN, a space, and the sum of 2 and 3. Nothing else."
PROBE_REPLY = "CORUN 5"
GROK_REFUSAL = "permission required:"
GROK_UNSANDBOXED = "sandbox could not be applied"
AGY_REFUSAL = "cannot prompt for, so it was auto-denied"
STALE_DAYS = 7
RETRY_MINUTES = 60
PROBE_TIMEOUT = 240
ASK_TIMEOUT = 1800
KEEP_RUNS_DAYS = 7
SAFE_TOKEN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/-]*$")
AGY_PREAMBLE = ("Read files with your file tools. Shell commands, file writes, MCP tools and web "
                "requests are denied in this session, so do not attempt them.\n\n")
# Grok's per-call sandbox profile: read the project and system paths, write only the per-call
# folder. A custom profile fails closed when it cannot be applied.
GROK_READ_TOOLS = "read_file,grep,list_dir"
GROK_WEB_TOOLS = "web_search,web_fetch"
GROK_SYSTEM_READ = ("/bin", "/usr", "/etc", "/lib", "/lib64", "/opt/homebrew", "/System",
                    "/Library", "/private/etc", "/dev")
# Environment passed to partners: only what a CLI needs to run and sign in.
ENV_KEEP = ("PATH", "HOME", "USER", "LOGNAME", "SHELL", "LANG", "TERM", "TZ",
            "SSL_CERT_FILE", "SSL_CERT_DIR", "NODE_EXTRA_CA_CERTS", "REQUESTS_CA_BUNDLE",
            "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY",
            "http_proxy", "https_proxy", "all_proxy", "no_proxy",
            "LC_ALL", "LC_CTYPE", "LC_MESSAGES", "LC_COLLATE", "LC_NUMERIC", "LC_TIME",
            "LC_MONETARY")
ENV_KEEP_CLI = {
    "codex": ("CODEX_HOME", "OPENAI_API_KEY", "OPENAI_BASE_URL"),
    "agy": ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GOOGLE_APPLICATION_CREDENTIALS",
            "GOOGLE_CLOUD_PROJECT"),
    "grok": ("GROK_HOME", "XAI_API_KEY", "GROK_API_KEY", "GROK_AUTH", "GROK_AUTH_PATH"),
}

EXIT_OK, EXIT_FAILED, EXIT_CLAUDE, EXIT_USAGE = 0, 2, 3, 4


class ConfigError(Exception):
    pass


# ---------------------------------------------------------------- locations and config

def config_dir():
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return os.path.join(base, "corun")


def roster_path():
    return os.path.join(config_dir(), "roster.json")


def runs_dir():
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "corun", "runs")


def run_dir():
    """A fresh per-call folder for corun's own files (task, reply, stderr). It lives in the
    user's cache folder, which no partner sandbox can write, so a partner cannot redirect
    these writes. Folders older than KEEP_RUNS_DAYS are removed."""
    base = runs_dir()
    os.makedirs(base, mode=0o700, exist_ok=True)
    cutoff = time.time() - KEEP_RUNS_DAYS * 86400
    for name in os.listdir(base):
        path = os.path.join(base, name)
        with contextlib.suppress(OSError):
            if os.path.isdir(path) and not os.path.islink(path) and os.path.getmtime(path) < cutoff:
                shutil.rmtree(path)
    return tempfile.mkdtemp(prefix=time.strftime("%Y%m%d-%H%M%S-"), dir=base)


def call_dir(project):
    """A fresh private folder in the system temp directory: the partner's working folder and
    the only place it may write. Removed after the call. Raises OSError when it would lie in
    the project or in any git work tree, where a partner would load that tree's agent config."""
    path = os.path.realpath(tempfile.mkdtemp(prefix="corun-"))
    real = os.path.realpath(project) if project else None
    bad = real and (path == real or path.startswith(real + os.sep))
    folder = os.path.dirname(path)
    while not bad and folder != os.path.dirname(folder):
        bad = os.path.exists(os.path.join(folder, ".git"))
        folder = os.path.dirname(folder)
    if bad:
        shutil.rmtree(path, ignore_errors=True)
        raise OSError("the temp folder %s is inside the project or a git work tree; set TMPDIR "
                      "to a plain temp folder" % os.path.dirname(path))
    return path


def load_models():
    """Return (models, digest) from the user's config folder if present, else the skill's own."""
    local = os.path.join(config_dir(), "models.json")
    path = local if os.path.isfile(local) else os.path.join(SKILL_DIR, "models.json")
    try:
        with open(path, "rb") as f:
            raw = f.read()
        models = json.loads(raw.decode("utf-8"))
    except (OSError, ValueError) as e:
        raise ConfigError("cannot read %s: %s" % (path, e))
    validate_models(models, path)
    return models, hashlib.sha256(raw).hexdigest()[:16]


def validate_models(m, path):
    def fail(msg):
        raise ConfigError("%s: %s" % (path, msg))
    if not isinstance(m, dict):
        fail("top level must be an object")
    partners, roles = m.get("partners"), m.get("roles")
    if not isinstance(partners, dict) or not isinstance(roles, dict) or not roles:
        fail("needs 'partners' and 'roles' objects")
    for name, p in partners.items():
        if not isinstance(p, dict) or not all(isinstance(p.get(k), str) for k in
                                              ("label", "cli", "model", "effort")):
            fail("partner %r needs label, cli, model and effort strings" % name)
        if p["cli"] not in ("codex", "agy", "grok"):
            fail("partner %r has unsupported cli %r" % (name, p["cli"]))
        for key in ("model", "effort"):
            if not SAFE_TOKEN.match(p[key]):
                fail("partner %r has an invalid %s %r" % (name, key, p[key]))
    fallbacks = m.get("claude_fallbacks", {})
    if not isinstance(fallbacks, dict) or not all(isinstance(v, str) for v in fallbacks.values()):
        fail("'claude_fallbacks' must map names to strings")
    for name, r in roles.items():
        if not isinstance(r, dict) or not isinstance(r.get("chain"), list) or not r["chain"]:
            fail("role %r needs a non-empty chain" % name)
        if not all(isinstance(n, str) for n in r["chain"]):
            fail("role %r has a chain entry that is not a string" % name)
        if not isinstance(r.get("web", False), bool):
            fail("role %r has a 'web' value that is not true or false" % name)
        pick = r.get("pick", 1)
        if not isinstance(pick, int) or isinstance(pick, bool) or pick < 1:
            fail("role %r has an invalid pick" % name)
    locations = m.get("cli_locations", {})
    if not isinstance(locations, dict) or not all(
            isinstance(v, list) and all(isinstance(x, str) for x in v) for v in locations.values()):
        fail("'cli_locations' must map tool names to lists of paths")


def now_iso():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def parse_time(value):
    """ISO timestamp to an aware datetime; naive values are taken as UTC; bad values give None."""
    if not isinstance(value, str):
        return None
    try:
        t = datetime.datetime.fromisoformat(value)
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=datetime.timezone.utc)


def age_minutes(value):
    t = parse_time(value)
    if t is None:
        return float("inf")
    return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 60


def find_bin(cli, models):
    """CORUN_<CLI>_BIN, then PATH, then known install locations."""
    env = os.environ.get("CORUN_%s_BIN" % cli.upper())
    if env:
        return env if os.access(env, os.X_OK) else None
    found = shutil.which(cli)
    if found:
        return found
    for path in models.get("cli_locations", {}).get(cli, []):
        path = os.path.expanduser(path)
        if os.access(path, os.X_OK):
            return path
    return None


# ---------------------------------------------------------------- running a partner

def run(cmd, cwd, timeout, stdin_text=None, env=None):
    """Run a command in its own process group; kill the whole group on timeout."""
    start = time.time()
    try:
        p = subprocess.Popen(cmd, cwd=cwd, env=env, stdin=subprocess.PIPE if stdin_text is not None
                             else subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, start_new_session=True)
    except OSError as e:
        return 127, "", str(e), 0.0
    data = stdin_text.encode("utf-8") if stdin_text is not None else None
    try:
        out, err = p.communicate(input=data, timeout=timeout)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        with contextlib.suppress(OSError):
            os.killpg(p.pid, signal.SIGKILL)
        out = b""
        try:
            out, _ = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            # A descendant that left the process group still holds the pipes.
            p.kill()
            for pipe in (p.stdout, p.stderr):
                with contextlib.suppress(OSError):
                    pipe.close()
            with contextlib.suppress(subprocess.TimeoutExpired):
                p.wait(timeout=5)
        rc, err = 124, b"timed out after %ds" % timeout
    return (rc, out.decode("utf-8", "replace"), err.decode("utf-8", "replace"),
            round(time.time() - start, 1))


def safe_write(path, text):
    """Write a file without following a symlink. Returns False instead of raising."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except OSError:
        return False
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
    except OSError:
        return False
    return True


def safe_read(path):
    try:
        fd = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    except OSError:
        return None
    with os.fdopen(fd, "rb") as f:
        return f.read().decode("utf-8", "replace")


def get_version(binary, cli):
    rc, out, err, _ = run([binary, "--version"], None, 30, env=partner_env(cli, tempfile.gettempdir()))
    text = (out or err).strip().splitlines()
    return text[0].strip() if rc == 0 and text else "unknown"


def partner_env(cli, tmp):
    """The environment a partner gets: a short allowlist plus that CLI's own variables."""
    keep = ENV_KEEP + ENV_KEEP_CLI.get(cli, ())
    env = {k: v for k, v in os.environ.items() if k in keep}
    env["TMPDIR"] = tmp
    if cli == "grok":
        # Keep Grok from running the user's Claude Code and Cursor hooks.
        env["GROK_CLAUDE_HOOKS_ENABLED"] = "0"
        env["GROK_CURSOR_HOOKS_ENABLED"] = "0"
    return env


def home_outside(project):
    """Every entry of the home folder that is not on the way to the project, so a deny rule
    on each leaves only the project readable there. Antigravity reads files outside its
    workspace without asking, and deny rules override allow rules."""
    home = os.path.realpath(os.path.expanduser("~"))
    keep = os.path.realpath(project) if project else None
    out, folder = [], home
    while True:
        try:
            names = sorted(os.listdir(folder))
        except OSError:
            return out + [folder]
        nxt = None
        for name in names:
            path = os.path.join(folder, name)
            if keep and (keep == path or keep.startswith(path + os.sep)):
                nxt = path
            else:
                out.append(path)
        if nxt is None or nxt == keep:
            return out
        folder = nxt


def links_out(project, limit=50000):
    """Symbolic links inside the project that lead outside it. Antigravity's allow rule names
    the project path, so a deny rule on each such link keeps it from reaching other files."""
    if not project:
        return []
    real, out, seen = os.path.realpath(project), [], 0
    for dirpath, dirnames, filenames in os.walk(project):
        for name in dirnames + filenames:
            seen += 1
            path = os.path.join(dirpath, name)
            if os.path.islink(path):
                target = os.path.realpath(path)
                if target != real and not target.startswith(real + os.sep):
                    out.append(path)
        if seen > limit:
            raise OSError("the project has more than %d entries, too many to check for links "
                          "that lead outside it; name a smaller folder" % limit)
    return out


def read_denials(paths):
    """read_file deny rules for paths. A path holding a glob character also gets a form with
    each such character replaced by '?', so the rule matches whether or not Antigravity reads
    the target as a pattern."""
    rules = []
    for p in paths:
        rules.append("read_file(%s)" % p)
        if re.search(r"[*?\[\]]", p):
            rules.append("read_file(%s)" % re.sub(r"[*?\[\]]", "?", p))
    return rules


def toml_list(items):
    return "[" + ", ".join(json.dumps(i) for i in items) + "]"


def build_command(spec, binary, prompt, project, call, records, web):
    """Return (cmd, cwd, stdin_text) for one partner call, or raise OSError when the call
    folder cannot be prepared. Every partner works in `call`, a fresh private temp folder that
    is its only writable place, so the project's own agent config (AGENTS.md, .codex/,
    .agents/, .grok/) is never loaded. The prompt never appears on the command line."""
    cli, model, effort = spec["cli"], spec["model"], spec["effort"]
    if project:
        prompt = ("The project folder to read is %s. Read it with your file tools; do not try "
                  "to modify anything.\n\n%s" % (project, prompt))
    if cli == "codex":
        cmd = [binary, "exec", "--ignore-user-config", "--ignore-rules", "-m", model,
               "-c", "model_reasoning_effort=%s" % effort, "-s", "read-only",
               "--skip-git-repo-check", "--ephemeral", "-C", call,
               "-o", os.path.join(records, "last_message.txt"), "-"]
        return cmd, call, prompt
    task = os.path.join(call, "task.md")
    if cli == "agy":
        if not safe_write(task, AGY_PREAMBLE + prompt):
            raise OSError("cannot write %s" % task)
        settings_file = os.path.join(call, "settings.json")
        allow = ["read_file(%s)" % task] + (["read_file(%s)" % project] if project else [])
        deny = ["write_file(*)", "command(*)", "mcp(*)", "read_url(*)", "execute_url(*)"]
        deny += read_denials([settings_file] + home_outside(project) + links_out(project))
        if not safe_write(settings_file, json.dumps({"permissions": {"allow": allow, "deny": deny}})):
            raise OSError("cannot write %s" % settings_file)
        cmd = [binary, "--model", model, "--sandbox", "--disable-slash-commands",
               "--settings", settings_file,
               "-p=Read the task in %s and carry it out exactly." % task]
        return cmd, call, None
    if cli == "grok":
        os.makedirs(os.path.join(call, ".grok"), mode=0o700)
        reads = ([project] if project else []) + [p for p in GROK_SYSTEM_READ if os.path.isdir(p)]
        # A random name, so no profile of the same name in the user's own sandbox.toml (which
        # Grok would prefer) can stand in for this one.
        name = "corun-" + os.urandom(8).hex()
        profile = ("[profiles.%s]\nextends = \"minimal\"\nrestrict_network = true\n"
                   "workspace_write = true\nread_only = %s\n" % (name, toml_list(reads)))
        if not (safe_write(os.path.join(call, ".grok", "sandbox.toml"), profile)
                and safe_write(task, prompt)):
            raise OSError("cannot write the Grok task or sandbox profile in %s" % call)
        # Only read tools (no shell, no writes, no network), or for a web role only web tools.
        tools = ["--tools", GROK_WEB_TOOLS] if web else ["--tools", GROK_READ_TOOLS,
                                                          "--disable-web-search"]
        cmd = [binary, "--always-approve", "--sandbox", name, "--deny", "MCPTool(*)",
               "--disallowed-tools", "Agent", "--no-memory", "-m", model,
               "--reasoning-effort", effort, "--cwd", call] + tools + ["--prompt-file", task]
        return cmd, call, None
    raise ConfigError("unsupported cli %r" % cli)


def call_partner(spec, binary, prompt, project, timeout, web=False):
    """Run one partner on a prompt. Returns (ok, text, error, seconds, records, refused).
    refused is True when the partner works but refused a tool call this task needed; such a
    failure says nothing about the partner's health. With web=True (a role marked "web" in
    models.json) the partner gets web search and no project access."""
    records = run_dir()
    try:
        call = call_dir(project)
    except OSError as e:
        return False, "", "cannot prepare the call: %s" % e, 0.0, records, False
    try:
        tmp = os.path.join(call, "tmp")
        os.makedirs(tmp, mode=0o700)
        cmd, cwd, stdin_text = build_command(spec, binary, prompt, None if web else project,
                                             call, records, web)
        rc, out, err, secs = run(cmd, cwd, timeout, stdin_text, partner_env(spec["cli"], tmp))
    except OSError as e:
        return False, "", "cannot prepare the call: %s" % e, 0.0, records, False
    finally:
        shutil.rmtree(call, ignore_errors=True)
    text = out
    if spec["cli"] == "codex":
        text = safe_read(os.path.join(records, "last_message.txt")) or ""
    safe_write(os.path.join(records, "reply.txt"), text)
    safe_write(os.path.join(records, "stderr.txt"), err)
    if rc == 124:
        return False, text, "timed out after %ss" % timeout, secs, records, False
    if spec["cli"] == "grok" and GROK_UNSANDBOXED in err:
        return False, text, "Grok's sandbox could not be applied", secs, records, False
    if spec["cli"] == "grok" and any(l.startswith(GROK_REFUSAL) for l in err.splitlines()):
        return False, text, "a tool call was refused for lack of approval", secs, records, True
    if spec["cli"] == "agy" and AGY_REFUSAL in err:
        return False, text, "a tool call was refused for lack of approval", secs, records, True
    if rc != 0:
        return False, text, "exit %s: %s" % (rc, last_line(err) or last_line(out)), secs, records, False
    if not text.strip():
        return False, text, "empty reply (%s)" % (last_line(err) or "no output"), secs, records, False
    return True, text, "", secs, records, False


def last_line(s):
    lines = [l for l in (s or "").strip().splitlines() if l.strip()]
    return lines[-1][:200] if lines else ""


# ---------------------------------------------------------------- roster

@contextlib.contextmanager
def roster_lock():
    try:
        os.makedirs(config_dir(), mode=0o700, exist_ok=True)
        f = open(os.path.join(config_dir(), "roster.lock"), "a")
    except OSError as e:
        print("corun: warning: cannot lock the roster: %s" % e, file=sys.stderr)
        yield
        return
    with f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)


def load_roster():
    try:
        with open(roster_path(), encoding="utf-8") as f:
            r = json.load(f)
    except (OSError, ValueError):
        return None
    if not isinstance(r, dict) or not isinstance(r.get("partners"), dict) \
            or not isinstance(r.get("roles"), dict):
        return None
    if not all(isinstance(p, dict) and isinstance(p.get("ok"), bool)
               and all(isinstance(p.get(k), str) for k in ("label", "model", "effort"))
               for p in r["partners"].values()):
        return None
    if not all(isinstance(v, list) and all(isinstance(n, str) for n in v)
               for v in r["roles"].values()):
        return None
    return r


def save_roster(roster):
    """Write the roster atomically. A failed write is reported and the in-memory roster is
    still used, so a read-only or full disk never stops fallback."""
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="roster.", suffix=".tmp", dir=config_dir())
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(roster, f, indent=2)
        os.replace(tmp, roster_path())
    except OSError as e:
        print("corun: warning: cannot save the roster: %s" % e, file=sys.stderr)
        if tmp:
            with contextlib.suppress(OSError):
                os.unlink(tmp)


def resolve_roles(models, partners):
    fallbacks = models.get("claude_fallbacks", {})
    roles = {}
    for role, spec in models["roles"].items():
        picked = []
        for name in spec["chain"]:
            if name in fallbacks or partners.get(name, {}).get("ok"):
                picked.append(name)
            if len(picked) == spec.get("pick", 1):
                break
        roles[role] = picked
    return roles


def probe(name, spec, models):
    binary = find_bin(spec["cli"], models)
    entry = {"label": spec["label"], "cli": spec["cli"], "model": spec["model"],
             "effort": spec["effort"], "checked_at": now_iso()}
    if not binary:
        entry.update(ok=False, version="", error="%s not installed" % spec["cli"], seconds=0)
        return name, entry
    entry["version"] = get_version(binary, spec["cli"])
    ok, text, error, secs, _, _ = call_partner(spec, binary, PROBE_PROMPT, None, PROBE_TIMEOUT)
    if ok and text.strip() != PROBE_REPLY:
        ok, error = False, "unexpected reply: %s" % last_line(text)
    entry.update(ok=ok, error=error, seconds=secs)
    return name, entry


def check(models, digest, only=None):
    names = [n for n in models["partners"] if not only or n in only]
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(names) or 1) as pool:
        results = list(pool.map(lambda n: probe(n, models["partners"][n], models), names))
    with roster_lock():
        roster = load_roster() or {"partners": {}, "roles": {}}
        for name, entry in results:
            roster["partners"][name] = entry
        for name in list(roster["partners"]):
            if name not in models["partners"]:
                del roster["partners"][name]
        if not only or "checked_at" not in roster:
            roster["checked_at"] = now_iso()
            roster["models_digest"] = digest
            roster["models_updated"] = models.get("updated", "")
        roster["roles"] = resolve_roles(models, roster["partners"])
        save_roster(roster)
    return roster


def mark_failed(models, name, error):
    try:
        _mark_failed(models, name, error)
    except OSError as e:
        print("corun: warning: cannot record the failure of %s: %s" % (name, e), file=sys.stderr)


def _mark_failed(models, name, error):
    with roster_lock():
        roster = load_roster()
        if roster is None or name not in roster["partners"]:
            return
        roster["partners"][name].update(ok=False, error=error, checked_at=now_iso())
        roster["roles"] = resolve_roles(models, roster["partners"])
        save_roster(roster)


def stale_reason(roster, models, digest):
    if not roster:
        return "no usable roster"
    if roster.get("models_digest") != digest:
        return "models.json changed"
    if set(roster["partners"]) != set(models["partners"]):
        return "partner list changed"
    known = set(roster["partners"]) | set(models.get("claude_fallbacks", {}))
    if set(roster["roles"]) != set(models["roles"]) or \
            any(n not in known for names in roster["roles"].values() for n in names):
        return "roster roles do not match models.json"
    checked = parse_time(roster.get("checked_at"))
    if checked is None:
        return "roster has no check time"
    days = (datetime.datetime.now(datetime.timezone.utc) - checked).days
    if days >= STALE_DAYS:
        return "roster is %d days old" % days
    return ""


def declaration(roster, models):
    fallbacks = models.get("claude_fallbacks", {})
    rows = []
    for role, names in roster["roles"].items():
        for name in names:
            if name in fallbacks:
                rows.append((role, fallbacks[name], "same-family fallback"))
            else:
                p = roster["partners"][name]
                rows.append((role, "%s (%s, %s)" % (p["label"], p["model"], p["effort"]),
                             "PASS %ss" % p.get("seconds", "?")))
    w = max([len(r[1]) for r in rows] + [24]) + 2
    lines = ["Corun roster, checked %s (models.json %s)"
             % (roster.get("checked_at", "?"), models.get("updated", "")), "",
             "%-10s%-*s%s" % ("ROLE", w, "ASSIGNED (model, effort)", "STATUS")]
    lines += ["%-10s%-*s%s" % (r[0], w, r[1], r[2]) for r in rows]
    bad = ["unavailable: %s (%s): %s" % (p.get("label", n), n, p.get("error", ""))
           for n, p in roster["partners"].items() if not p.get("ok")]
    return "\n".join(lines + ([""] + bad if bad else []))


def fresh_roster(models, digest):
    roster = load_roster()
    reason = stale_reason(roster, models, digest)
    if reason:
        print("corun: re-checking partners (%s)" % reason, file=sys.stderr)
        roster = check(models, digest)
        print(declaration(roster, models), file=sys.stderr)
    return roster


# ---------------------------------------------------------------- ask

def ask(models, digest, role, prompt, project, exclude, partner, timeout):
    if role not in models["roles"]:
        print("corun: unknown role %r; roles: %s" % (role, ", ".join(models["roles"])),
              file=sys.stderr)
        return EXIT_USAGE
    if partner and partner not in models["partners"]:
        print("corun: unknown partner %r" % partner, file=sys.stderr)
        return EXIT_USAGE
    roster = fresh_roster(models, digest)
    fallbacks = models.get("claude_fallbacks", {})
    chain = [partner] if partner else models["roles"][role]["chain"]
    for name in chain:
        if name in fallbacks:
            # Claude fallbacks are never excluded: a second same-family reviewer is a second
            # fresh subagent.
            print("corun: role %s falls back to a %s (same-family). Run the task as that "
                  "subagent." % (role, fallbacks[name]), file=sys.stderr)
            return EXIT_CLAUDE
        if name in exclude:
            continue
        spec = models["partners"].get(name)
        if spec is None:
            print("corun: skipping %r in the %s chain: not a partner in models.json"
                  % (name, role), file=sys.stderr)
            continue
        binary = find_bin(spec["cli"], models)
        if not binary:
            continue
        state = roster["partners"].get(name, {})
        if not state.get("ok") and age_minutes(state.get("checked_at")) >= RETRY_MINUTES:
            print("corun: %s failed earlier (%s), re-checking it" % (name, state.get("error", "")),
                  file=sys.stderr)
            roster = check(models, digest, only=[name])
            state = roster["partners"][name]
        elif state.get("ok") and get_version(binary, spec["cli"]) != state.get("version"):
            print("corun: %s changed version, re-checking it" % name, file=sys.stderr)
            roster = check(models, digest, only=[name])
            state = roster["partners"][name]
        if not state.get("ok"):
            continue
        print("corun: role=%s partner=%s (%s, %s, %s)"
              % (role, name, spec["label"], spec["model"], spec["effort"]), file=sys.stderr)
        ok, text, error, secs, work, refused = call_partner(spec, binary, prompt, project, timeout,
                                                            web=models["roles"][role].get("web", False))
        print("corun: %s %s in %ss; files in %s" % (name, "ok" if ok else "FAILED: " + error,
                                                    secs, work), file=sys.stderr)
        if ok:
            sys.stdout.write(text if text.endswith("\n") else text + "\n")
            return EXIT_OK
        if not refused:
            mark_failed(models, name, error)
    print("corun: no partner succeeded for role %s" % role, file=sys.stderr)
    return EXIT_FAILED


# ---------------------------------------------------------------- command line

def main(argv=None):
    ap = argparse.ArgumentParser(prog="corun", description="Partner AI calls for the Corun skill.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="probe partners and print the declaration")
    c.add_argument("--only", nargs="+", help="probe only these partners")
    sub.add_parser("status", help="print the declaration")
    a = sub.add_parser("ask", help="send a task to a role")
    a.add_argument("role")
    a.add_argument("--prompt-file", required=True, help="file holding the task ('-' for stdin)")
    a.add_argument("--project", default=os.getcwd(), help="project folder partners may read")
    a.add_argument("--exclude", nargs="*", default=[], help="partners to skip")
    a.add_argument("--partner", help="use exactly this partner")
    a.add_argument("--timeout", type=int, default=ASK_TIMEOUT)
    s = sub.add_parser("scan", help="pre-publish privacy scan")
    s.add_argument("dir")
    args = ap.parse_args(argv)

    if args.cmd == "scan":
        sys.path.insert(0, HERE)
        import scan as scanner
        return scanner.main([args.dir])

    try:
        models, digest = load_models()
        if args.cmd == "check":
            print(declaration(check(models, digest, only=args.only), models))
            return EXIT_OK
        if args.cmd == "status":
            print(declaration(fresh_roster(models, digest), models))
            return EXIT_OK
        try:
            if args.prompt_file == "-":
                prompt = sys.stdin.read()
            else:
                with open(args.prompt_file, encoding="utf-8", errors="replace") as f:
                    prompt = f.read()
        except OSError as e:
            print("corun: cannot read prompt file: %s" % e, file=sys.stderr)
            return EXIT_USAGE
        prompt = prompt.replace("\x00", "")
        if not prompt.strip():
            print("corun: empty prompt", file=sys.stderr)
            return EXIT_USAGE
        project = os.path.abspath(args.project)
        if not os.path.isdir(project):
            print("corun: project folder not found: %s" % project, file=sys.stderr)
            return EXIT_USAGE
        return ask(models, digest, args.role, prompt, project, set(args.exclude),
                   args.partner, args.timeout)
    except ConfigError as e:
        print("corun: %s" % e, file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
