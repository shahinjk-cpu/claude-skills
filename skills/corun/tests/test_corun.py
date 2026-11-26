"""Tests for scripts/corun.py and scripts/scan.py, using stub CLIs (no real model calls).

Run: python3 -m unittest discover -s tests -v   (from the skill folder)
"""
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CORUN = os.path.join(SKILL, "scripts", "corun.py")
STUB = os.path.join(SKILL, "tests", "stub_cli.py")


class Env:
    """An isolated config folder, temp folder, stub CLIs and call log."""

    def __init__(self):
        self.root = tempfile.mkdtemp(prefix="corun-test-")
        self.bin = os.path.join(self.root, "bin")
        os.makedirs(self.bin)
        self.log = os.path.join(self.root, "calls.jsonl")
        self.project = tempfile.mkdtemp(prefix="corun-project-", dir=os.path.expanduser("~"))
        for cli in ("agy", "codex", "grok"):
            path = os.path.join(self.bin, cli)
            shutil.copy(STUB, path)
            os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC)
        self.env = {
            "PATH": "/usr/bin:/bin",
            "HOME": self.root,
            "XDG_CONFIG_HOME": os.path.join(self.root, "config"),
            "TMPDIR": os.path.join(self.root, "tmp"),
            "STUB_LOG": self.log,
            "CORUN_AGY_BIN": os.path.join(self.bin, "agy"),
            "CORUN_CODEX_BIN": os.path.join(self.bin, "codex"),
            "CORUN_GROK_BIN": os.path.join(self.bin, "grok"),
        }
        os.makedirs(self.env["TMPDIR"])

    def run(self, *args, stdin=None, **extra):
        env = dict(self.env, **extra)
        with open(os.path.join(self.bin, "stub_env.json"), "w") as f:
            json.dump({k: v for k, v in env.items() if k.startswith("STUB_")}, f)
        p = subprocess.run([sys.executable, CORUN] + list(args), env=env, input=stdin,
                           capture_output=True, text=True, timeout=120)
        return p.returncode, p.stdout, p.stderr

    def prompt(self, text="Do the task."):
        path = os.path.join(self.root, "prompt.md")
        with open(path, "w") as f:
            f.write(text)
        return path

    def roster(self):
        with open(os.path.join(self.env["XDG_CONFIG_HOME"], "corun", "roster.json")) as f:
            return json.load(f)

    def calls(self, cli=None):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            rows = [json.loads(l) for l in f]
        rows = [r for r in rows if "argv" in r and r["argv"] != ["--version"]]
        return [r for r in rows if cli is None or r["cli"] == cli]

    def prompts(self, cli):
        if not os.path.exists(self.log):
            return []
        with open(self.log) as f:
            rows = [json.loads(l) for l in f]
        return [r["prompt"] for r in rows if "prompt" in r and r["cli"] == cli]

    def write_roster(self, data):
        d = os.path.join(self.env["XDG_CONFIG_HOME"], "corun")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "roster.json"), "w") as f:
            f.write(data if isinstance(data, str) else json.dumps(data))

    def clear_log(self):
        if os.path.exists(self.log):
            os.remove(self.log)

    def close(self):
        shutil.rmtree(self.root, ignore_errors=True)
        shutil.rmtree(self.project, ignore_errors=True)


class CorunTests(unittest.TestCase):
    def setUp(self):
        self.e = Env()

    def tearDown(self):
        self.e.close()

    def test_check_all_partners_pass(self):
        rc, out, err = self.e.run("check")
        self.assertEqual(rc, 0, err)
        r = self.e.roster()
        self.assertTrue(all(p["ok"] for p in r["partners"].values()))
        self.assertEqual(r["roles"]["planner"], ["neon"])
        self.assertEqual(r["roles"]["reviewer"], ["grok", "sol61"])
        self.assertEqual(r["roles"]["runner"], ["grok"])
        self.assertIn("Gemini 4 Neon (gemini-4-neon-high, high)", out)

    def test_safety_flags_on_every_partner(self):
        self.e.run("check")
        self.e.clear_log()
        self.e.run("ask", "worker", "--prompt-file", self.e.prompt(), "--project", self.e.project,
                   "--partner", "sol62")
        self.e.run("ask", "worker", "--prompt-file", self.e.prompt(), "--project", self.e.project,
                   "--partner", "neon")
        self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(), "--project",
                   self.e.project)
        project = os.path.realpath(self.e.project)
        codex = self.e.calls("codex")[0]["argv"]
        self.assertIn("read-only", codex[codex.index("-s") + 1])
        self.assertIn("--ignore-user-config", codex)
        self.assertIn("--ignore-rules", codex)
        self.assertEqual(codex[-1], "-")
        agy = self.e.calls("agy")[0]["argv"]
        self.assertNotIn("--mode", agy)
        self.assertIn("--sandbox", agy)
        settings = json.loads(self.e.calls("agy")[0]["profile"])["permissions"]
        for rule in ("write_file(*)", "command(*)", "mcp(*)", "read_url(*)", "execute_url(*)"):
            self.assertIn(rule, settings["deny"])
        self.assertIn("read_file(%s)" % project, settings["allow"])
        grok_call = self.e.calls("grok")[0]
        grok = grok_call["argv"]
        self.assertIn("--always-approve", grok)
        self.assertTrue(grok[grok.index("--sandbox") + 1].startswith("corun-"))
        self.assertIn("[profiles.%s]" % grok[grok.index("--sandbox") + 1], grok_call["profile"])
        self.assertEqual(grok[grok.index("--tools") + 1], "read_file,grep,list_dir")
        self.assertEqual(grok[grok.index("--disallowed-tools") + 1], "Agent")
        self.assertEqual(grok[grok.index("--deny") + 1], "MCPTool(*)")
        self.assertIn("--no-memory", grok)
        self.assertIn("--disable-web-search", grok)
        self.assertIn('extends = "minimal"', grok_call["profile"])
        self.assertIn("workspace_write = true", grok_call["profile"])
        self.assertIn(json.dumps(project), grok_call["profile"])
        self.assertNotIn("read_write", grok_call["profile"])
        # No partner works in the project, and each gets its own temp folder as TMPDIR.
        for call in self.e.calls():
            self.assertNotEqual(os.path.realpath(call["cwd"]), project)
            self.assertTrue(call["tmpdir"].startswith(os.path.realpath(call["cwd"])))
        # Everything else in the home folder is denied, since Antigravity reads outside its
        # workspace without asking.
        with open(os.path.join(self.e.root, "dotfile"), "w") as f:
            f.write("x")
        self.e.clear_log()
        self.e.run("ask", "worker", "--prompt-file", self.e.prompt(), "--project", self.e.project,
                   "--partner", "neon")
        agy = self.e.calls("agy")[0]["argv"]
        deny = json.loads(self.e.calls("agy")[0]["profile"])["permissions"]["deny"]
        self.assertIn("read_file(%s)" % os.path.realpath(os.path.join(self.e.root, "dotfile")),
                      deny)
        self.assertFalse(any(project.startswith(r[10:-1]) for r in deny if r.startswith("read_file(")))
        self.assertTrue(all(r.startswith("read_file(") for r in settings["allow"]))
        self.assertEqual(grok[grok.index("--reasoning-effort") + 1], "high")
        codex_effort = codex[codex.index("-c") + 1]
        self.assertEqual(codex_effort, "model_reasoning_effort=high")

    def test_grok_works_in_its_own_temp_folder(self):
        self.e.run("check")
        self.e.clear_log()
        rc, out, err = self.e.run("ask", "runner", "--prompt-file", self.e.prompt(),
                                  "--project", self.e.project)
        self.assertEqual(rc, 0, err)
        call = self.e.calls("grok")[0]
        work = call["argv"][call["argv"].index("--cwd") + 1]
        self.assertTrue(work.startswith(os.path.realpath(self.e.env["TMPDIR"])), work)
        self.assertEqual(os.path.realpath(call["cwd"]), os.path.realpath(work))
        self.assertFalse(os.path.exists(work), "the per-call folder was not removed")
        # The runner searches the web and gets no project access.
        self.assertNotIn("--disable-web-search", call["argv"])
        self.assertEqual(call["argv"][call["argv"].index("--tools") + 1], "web_search,web_fetch")
        self.assertNotIn(os.path.realpath(self.e.project), call["profile"])
        self.assertNotIn(self.e.project, self.e.prompts("grok")[-1])

    def test_missing_partner_falls_back(self):
        rc, out, err = self.e.run("check", CORUN_GROK_BIN="/nonexistent/grok")
        self.assertEqual(rc, 0, err)
        r = self.e.roster()
        self.assertFalse(r["partners"]["grok"]["ok"])
        self.assertEqual(r["roles"]["runner"], ["claude-haiku"])
        self.assertEqual(r["roles"]["reviewer"], ["sol61", "neon"])
        self.assertIn("same-family fallback", out)

    def test_only_claude_left(self):
        rc, out, err = self.e.run("check", CORUN_GROK_BIN="/x/grok", CORUN_AGY_BIN="/x/agy",
                                  CORUN_CODEX_BIN="/x/codex")
        r = self.e.roster()
        self.assertEqual(r["roles"]["worker"], ["claude-sonnet"])
        self.assertEqual(r["roles"]["reviewer"], ["claude-opus"])
        rc, out, err = self.e.run("ask", "worker", "--prompt-file", self.e.prompt(),
                                  CORUN_GROK_BIN="/x/grok", CORUN_AGY_BIN="/x/agy",
                                  CORUN_CODEX_BIN="/x/codex")
        self.assertEqual(rc, 3)
        self.assertIn("Claude Sonnet subagent", err)

    def test_ask_success_prints_reply(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt(),
                                  "--project", self.e.project)
        self.assertEqual(rc, 0, err)
        self.assertIn("CORUN 5 from agy", out)
        self.assertIn("role=planner partner=neon", err)

    def test_codex_reply_comes_from_output_file(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "checker", "--prompt-file", self.e.prompt(),
                                  "--project", self.e.project)
        self.assertEqual(rc, 0, err)
        self.assertIn("CORUN 5 from codex", out)
        self.assertNotIn("progress noise", out)

    def test_permission_refusal_counts_as_failure(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "runner", "--prompt-file", self.e.prompt(),
                                  STUB_GROK_MODE="perm")
        self.assertEqual(rc, 3, err)
        self.assertIn("refused for lack of approval", err)
        # A refusal is a task-level failure: the partner stays healthy in the roster.
        self.assertTrue(self.e.roster()["partners"]["grok"]["ok"])

    def test_failure_falls_through_chain(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "worker", "--prompt-file", self.e.prompt(),
                                  STUB_AGY_MODE="fail")
        self.assertEqual(rc, 0, err)
        self.assertIn("CORUN 5 from grok", out)
        self.assertIn("neon FAILED", err)

    def test_empty_reply_is_failure(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt(),
                                  STUB_AGY_MODE="empty")
        self.assertEqual(rc, 0, err)
        self.assertIn("empty reply", err)
        self.assertIn("CORUN 5 from codex", out)

    def test_exclude_gives_second_reviewer(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(),
                                  "--exclude", "grok")
        self.assertEqual(rc, 0, err)
        self.assertIn("partner=sol61", err)

    def test_timeout_falls_back(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "runner", "--prompt-file", self.e.prompt(),
                                  "--timeout", "2", STUB_GROK_MODE="slow")
        self.assertEqual(rc, 3, err)
        self.assertIn("timed out", err)

    def test_prompt_never_on_command_line(self):
        self.e.run("check")
        self.e.clear_log()
        secret_text = "confidential-" + "q" * 40
        for role in ("planner", "runner"):
            rc, out, err = self.e.run("ask", role, "--prompt-file", self.e.prompt(secret_text))
            self.assertEqual(rc, 0, err)
        for call in self.e.calls():
            self.assertFalse(any(secret_text in a for a in call["argv"]), call["cli"])
        self.assertIn(secret_text, self.e.prompts("agy")[-1])

    def test_prompt_from_stdin(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", "-", stdin="Plan it.")
        self.assertEqual(rc, 0, err)

    def test_first_ask_runs_check(self):
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 0, err)
        self.assertIn("re-checking partners (no usable roster)", err)
        self.assertIn("ROLE", err)

    def test_version_change_rechecks_partner(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt(),
                                  STUB_AGY_VERSION="agy 2.0")
        self.assertEqual(rc, 0, err)
        self.assertIn("neon changed version", err)
        self.assertEqual(self.e.roster()["partners"]["neon"]["version"], "agy 2.0")

    def test_models_override_and_staleness(self):
        self.e.run("check")
        with open(os.path.join(SKILL, "models.json")) as f:
            models = json.load(f)
        models["updated"] = "2099-01-01"
        models["partners"]["neon"]["effort"] = "medium"
        path = os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun", "models.json")
        with open(path, "w") as f:
            json.dump(models, f)
        rc, out, err = self.e.run("status")
        self.assertEqual(rc, 0, err)
        self.assertIn("models.json changed", err)
        self.assertIn("gemini-4-neon-high, medium", out)

    def test_old_failure_is_retried(self):
        self.e.run("check", STUB_AGY_MODE="fail")
        r = self.e.roster()
        self.assertFalse(r["partners"]["neon"]["ok"])
        r["partners"]["neon"]["checked_at"] = "2000-01-01T00:00:00+00:00"
        with open(os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun", "roster.json"), "w") as f:
            json.dump(r, f)
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 0, err)
        self.assertIn("partner=neon", err)

    def test_prompts_starting_with_dashes(self):
        self.e.run("check")
        for role, cli in (("checker", "codex"), ("planner", "agy"), ("runner", "grok")):
            rc, out, err = self.e.run("ask", role, "--prompt-file", self.e.prompt("--- front matter"))
            self.assertEqual(rc, 0, err)
            self.assertIn("--- front matter", self.e.prompts(cli)[-1])

    def test_codex_reply_mentioning_permission_text_is_ok(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "checker", "--prompt-file",
                                  self.e.prompt("permission required: is a string in the code"),
                                  STUB_CODEX_MODE="echo")
        self.assertEqual(rc, 0, err)
        self.assertIn("permission required:", out)

    def test_codex_without_output_file_fails(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "checker", "--prompt-file", self.e.prompt(),
                                  STUB_CODEX_MODE="noout")
        self.assertIn("empty reply", err)
        self.assertNotIn("progress noise", out)

    def test_probe_rejects_echoed_prompt(self):
        rc, out, err = self.e.run("check", STUB_AGY_MODE="echo")
        self.assertFalse(self.e.roster()["partners"]["neon"]["ok"])

    def test_invalid_utf8_from_partner(self):
        self.e.run("check")
        path = os.path.join(self.e.bin, "agy")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n[ \"$1\" = --version ] && { echo agy 1.0; exit 0; }\n"
                    "printf 'ok \\377 bytes\\n'\n")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 0, err)
        self.assertIn("ok", out)

    def test_corrupt_roster_is_rebuilt(self):
        for bad in ("[1]", "{not json", json.dumps({"partners": [], "roles": {}})):
            self.e.write_roster(bad)
            rc, out, err = self.e.run("status")
            self.assertEqual(rc, 0, err)
            self.assertIn("no usable roster", err)

    def test_naive_timestamps(self):
        self.e.run("check")
        r = self.e.roster()
        r["checked_at"] = "2026-01-01T00:00:00"
        r["partners"]["neon"].update(ok=False, checked_at="2026-01-01T00:00:00")
        self.e.write_roster(r)
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 0, err)

    def test_unknown_chain_entry_is_skipped(self):
        with open(os.path.join(SKILL, "models.json")) as f:
            models = json.load(f)
        models["roles"]["planner"]["chain"] = ["retired", "neon", "claude-opus"]
        d = os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "models.json"), "w") as f:
            json.dump(models, f)
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 0, err)
        self.assertIn("skipping 'retired'", err)

    def test_invalid_models_json(self):
        d = os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "models.json"), "w") as f:
            f.write("{}")
        rc, out, err = self.e.run("status")
        self.assertEqual(rc, 4, err)

    def test_missing_prompt_file(self):
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", "/nonexistent/p.md")
        self.assertEqual(rc, 4, err)

    def test_second_claude_reviewer(self):
        missing = dict(CORUN_GROK_BIN="/x/grok", CORUN_AGY_BIN="/x/agy", CORUN_CODEX_BIN="/x/codex")
        self.e.run("check", **missing)
        rc, out, err = self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(),
                                  "--exclude", "claude-opus", **missing)
        self.assertEqual(rc, 3, err)

    def test_parallel_asks_keep_roster_valid(self):
        self.e.run("check")
        env = dict(self.e.env, STUB_AGY_MODE="fail", STUB_CODEX_MODE="fail")
        with open(os.path.join(self.e.bin, "stub_env.json"), "w") as f:
            json.dump({k: v for k, v in env.items() if k.startswith("STUB_")}, f)
        procs = [subprocess.Popen([sys.executable, CORUN, "ask", "planner", "--prompt-file",
                                   self.e.prompt()], env=env, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE) for _ in range(4)]
        for p in procs:
            p.communicate(timeout=120)
        r = self.e.roster()
        self.assertFalse(r["partners"]["neon"]["ok"])
        self.assertFalse(r["partners"]["sol62"]["ok"])

    def test_timeout_kills_child_processes(self):
        self.e.run("check")
        marker = os.path.join(self.e.root, "child_alive")
        path = os.path.join(self.e.bin, "grok")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n[ \"$1\" = --version ] && { echo grok 1.0; exit 0; }\n"
                    "(sleep 4; touch %s) &\nsleep 30\n" % marker)
        rc, out, err = self.e.run("ask", "runner", "--prompt-file", self.e.prompt(), "--timeout", "1")
        import time
        time.sleep(5)
        self.assertFalse(os.path.exists(marker), "child of a timed-out partner kept running")

    def test_refusal_does_not_mark_partner_unavailable(self):
        self.e.run("check")
        path = os.path.join(self.e.bin, "agy")
        with open(path, "w") as f:
            f.write("#!/bin/sh\n[ \"$1\" = --version ] && { echo agy 1.0; exit 0; }\n"
                    "echo 'jetski: no output produced, a tool required the write_file permission "
                    "that headless mode cannot prompt for, so it was auto-denied.' >&2\n")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt())
        self.assertIn("refused", err)
        self.assertTrue(self.e.roster()["partners"]["neon"]["ok"])

    def test_corun_files_outside_partner_writable_temp(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "runner", "--prompt-file", self.e.prompt())
        files = err.split("files in ")[-1].strip()
        self.assertTrue(files.startswith(os.path.join(self.e.root, ".cache", "corun", "runs")), files)
        self.assertFalse(files.startswith(self.e.env["TMPDIR"]))

    def test_nul_in_prompt(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt("a\x00b"))
        self.assertEqual(rc, 0, err)

    def test_roster_with_null_role(self):
        self.e.run("check")
        r = self.e.roster()
        r["roles"]["planner"] = None
        self.e.write_roster(r)
        rc, out, err = self.e.run("status")
        self.assertEqual(rc, 0, err)

    def test_project_in_temp_is_read_only_for_grok(self):
        self.e.run("check")
        self.e.clear_log()
        project = os.path.join(self.e.root, "project-in-temp")
        os.makedirs(project)
        rc, out, err = self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(),
                                  "--project", project)
        self.assertEqual(rc, 0, err)
        profile = self.e.calls("grok")[0]["profile"]
        self.assertNotIn("read_write", profile)
        self.assertIn("read_only", profile)

    def test_grok_profile_name_differs_per_call(self):
        self.e.run("check")
        self.e.clear_log()
        for _ in range(2):
            self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt())
        names = [c["argv"][c["argv"].index("--sandbox") + 1] for c in self.e.calls("grok")]
        self.assertEqual(len(set(names)), 2)

    def test_call_folder_inside_project_is_refused(self):
        self.e.run("check")
        inner = os.path.join(self.e.project, "scratch")
        os.makedirs(inner)
        rc, out, err = self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(),
                                  "--project", self.e.project, TMPDIR=inner)
        self.assertNotEqual(rc, 0)
        self.assertIn("inside the project or a git work tree", err)

    def test_links_leaving_the_project_are_denied_to_antigravity(self):
        self.e.run("check")
        outside = os.path.join(self.e.root, "secret.txt")
        with open(outside, "w") as f:
            f.write("s")
        os.symlink(outside, os.path.join(self.e.project, "link.txt"))
        self.e.clear_log()
        self.e.run("ask", "planner", "--prompt-file", self.e.prompt(), "--project", self.e.project)
        deny = json.loads(self.e.calls("agy")[0]["profile"])["permissions"]["deny"]
        self.assertIn("read_file(%s)" % os.path.join(self.e.project, "link.txt"), deny)
        self.assertNotIn(os.path.join(self.e.project, "link.txt"), " ".join(self.e.calls("agy")[0]["argv"]))

    def test_link_under_git_and_glob_names_are_denied(self):
        self.e.run("check")
        outside = os.path.join(self.e.root, "secret.txt")
        with open(outside, "w") as f:
            f.write("s")
        os.makedirs(os.path.join(self.e.project, ".git"))
        os.symlink(outside, os.path.join(self.e.project, ".git", "k"))
        with open(os.path.join(self.e.root, "a[b].txt"), "w") as f:
            f.write("s")
        self.e.clear_log()
        self.e.run("ask", "planner", "--prompt-file", self.e.prompt(), "--project", self.e.project)
        settings = json.loads(self.e.calls("agy")[0]["profile"])["permissions"]
        self.assertIn("read_file(%s)" % os.path.join(self.e.project, ".git", "k"), settings["deny"])
        glob = os.path.realpath(os.path.join(self.e.root, "a[b].txt"))
        self.assertIn("read_file(%s)" % glob, settings["deny"])
        self.assertIn("read_file(%s)" % glob.replace("[", "?").replace("]", "?"), settings["deny"])
        self.assertTrue(any(r.endswith("settings.json)") for r in settings["deny"]))
        self.assertFalse(any(r.endswith("settings.json)") for r in settings["allow"]))

    def test_grok_does_not_run_claude_or_cursor_hooks(self):
        self.e.run("check")
        for call in self.e.calls("grok"):
            self.assertIn("GROK_CLAUDE_HOOKS_ENABLED", call["env"])
            self.assertIn("GROK_CURSOR_HOOKS_ENABLED", call["env"])

    def test_environment_is_filtered(self):
        self.e.run("check", AWS_SECRET_ACCESS_KEY="x", GITHUB_TOKEN="y", XAI_API_KEY="z",
                   LC_PRIVATE_TOKEN="t")
        for call in self.e.calls():
            self.assertNotIn("AWS_SECRET_ACCESS_KEY", call["env"])
            self.assertNotIn("GITHUB_TOKEN", call["env"])
            self.assertNotIn("LC_PRIVATE_TOKEN", call["env"])
            self.assertIn("HOME", call["env"])
            self.assertEqual("XAI_API_KEY" in call["env"], call["cli"] == "grok")

    def test_agy_refusal_with_partial_answer_is_failure(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "planner", "--prompt-file", self.e.prompt(),
                                  STUB_AGY_MODE="permout")
        self.assertIn("neon FAILED", err)
        self.assertNotIn("partial answer", out)
        self.assertTrue(self.e.roster()["partners"]["neon"]["ok"])

    def test_unsandboxed_grok_is_failure(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "reviewer", "--prompt-file", self.e.prompt(),
                                  STUB_GROK_MODE="nosandbox")
        self.assertIn("sandbox could not be applied", err)
        self.assertIn("partner=sol61", err)

    def test_probe_needs_exact_reply(self):
        rc, out, err = self.e.run("check", STUB_CODEX_MODE="echo")
        self.assertFalse(self.e.roster()["partners"]["sol62"]["ok"])

    def test_invalid_model_tokens_rejected(self):
        d = os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun")
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(SKILL, "models.json")) as f:
            base = json.load(f)
        for bad in ({"model": "--dangerous"}, {"effort": "high extra"}, {"model": "a\"b"}):
            m = json.loads(json.dumps(base))
            m["partners"]["neon"].update(bad)
            with open(os.path.join(d, "models.json"), "w") as f:
                json.dump(m, f)
            rc, out, err = self.e.run("status")
            self.assertEqual(rc, 4, (bad, err))
        m = json.loads(json.dumps(base))
        m["roles"]["planner"]["chain"] = [["neon"]]
        with open(os.path.join(d, "models.json"), "w") as f:
            json.dump(m, f)
        rc, out, err = self.e.run("status")
        self.assertEqual(rc, 4, err)

    def test_roster_naming_missing_partner_is_rebuilt(self):
        self.e.run("check")
        r = self.e.roster()
        r["roles"]["planner"] = ["ghost"]
        self.e.write_roster(r)
        rc, out, err = self.e.run("status")
        self.assertEqual(rc, 0, err)
        self.assertIn("re-checking", err)

    def test_readonly_config_does_not_stop_fallback(self):
        self.e.run("check")
        d = os.path.join(self.e.env["XDG_CONFIG_HOME"], "corun")
        os.chmod(d, 0o500)
        try:
            rc, out, err = self.e.run("ask", "worker", "--prompt-file", self.e.prompt(),
                                      STUB_AGY_MODE="fail")
        finally:
            os.chmod(d, 0o700)
        self.assertEqual(rc, 0, err)
        self.assertIn("CORUN 5 from grok", out)

    def test_unknown_role(self):
        self.e.run("check")
        rc, out, err = self.e.run("ask", "boss", "--prompt-file", self.e.prompt())
        self.assertEqual(rc, 4)


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="corun-scan-")

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def scan(self, d):
        p = subprocess.run([sys.executable, CORUN, "scan", d], capture_output=True, text=True)
        return p.returncode, p.stdout + p.stderr

    def write(self, name, text):
        with open(os.path.join(self.dir, name), "w") as f:
            f.write(text)

    def test_clean(self):
        self.write("a.md", "Install to ~/.claude/skills/corun/ and run it.\n")
        rc, out = self.scan(self.dir)
        self.assertEqual(rc, 0, out)

    def test_findings(self):
        fake = "sk-ant-" + "api03-" + "A" * 40
        self.write("a.md", "path /Users/" + "somebody/x\nkey " + fake + "\nmail jo" + "@school.edu\n")
        self.write("roster.json", "{}")
        rc, out = self.scan(self.dir)
        self.assertEqual(rc, 1, out)
        for rule in ("home-path", "anthropic-key", "email", "forbidden-file"):
            self.assertIn(rule, out)
        self.assertNotIn("A" * 40, out)

    def test_allow_marker(self):
        self.write("a.md", "see /Users/" + "somebody/x  corun-scan: allow\n")
        rc, out = self.scan(self.dir)
        self.assertEqual(rc, 0, out)

    def test_unscanned_and_forbidden_files(self):
        with open(os.path.join(self.dir, "notes.md"), "wb") as f:
            f.write(("jo" + "@school.edu").encode("utf-16"))
        self.write(".env.local", "X=1\n")
        with open(os.path.join(self.dir, "logo.png"), "wb") as f:
            f.write(("jo" + "@school.edu").encode("utf-16"))
        rc, out = self.scan(self.dir)
        self.assertEqual(rc, 1, out)
        self.assertIn("notes.md:0: unscanned-file", out)
        self.assertIn(".env.local:0: forbidden-file", out)
        # A file that only claims to be an image is reported, not passed.
        self.assertIn("logo.png:0: unscanned-file", out)

    def test_allow_marker_never_exempts_secrets(self):
        self.write("a.md", "key sk-ant-" + "api03-" + "B" * 30 + "  corun-scan: allow\n")
        rc, out = self.scan(self.dir)
        self.assertEqual(rc, 1, out)

    def test_windows_paths_and_filenames(self):
        self.write("a.md", "D:\\" + "Users\\Alice\\project\n")
        self.write("from-jo" + "@school.edu.md", "nothing\n")
        rc, out = self.scan(self.dir)
        self.assertIn("home-path", out)
        self.assertIn("email", out)

    def test_more_secret_formats(self):
        samples = {
            "slack-token": "xox" + "b-" + "1234567890-abcdefghij",
            "gitlab-token": "gl" + "pat-" + "a" * 20,
            "npm-token": "np" + "m_" + "A" * 36,
            "stripe-key": "sk" + "_live_" + "B" * 24,
            "huggingface-token": "h" + "f_" + "C" * 34,
            "google-oauth": "ya" + "29." + "D" * 30,
            "bearer-token": "Authorization: Bear" + "er " + "E" * 30,
            "url-credentials": "https://bob:" + "hunter2x" + "@db.example.net/x",
            "credential-field": '{"refresh' + '_token": "' + "F" * 30 + '"}',
        }
        for rule, text in samples.items():
            self.write("a.md", text + "\n")
            rc, out = self.scan(self.dir)
            self.assertIn(rule, out, (rule, out))

    def test_home_path_forms(self):
        for text in ("C:/" + "Users/Alice/x", "see ~" + "alice/notes"):
            self.write("a.md", text + "\n")
            rc, out = self.scan(self.dir)
            self.assertIn("home-path", out, text)

    def test_png_text_chunk_is_scanned(self):
        import struct
        import zlib as z
        def chunk(kind, body):
            return (struct.pack(">I", len(body)) + kind + body
                    + struct.pack(">I", z.crc32(kind + body)))
        secret = ("gh" + "p_" + "G" * 36).encode()
        for c in (chunk(b"tEXt", b"Comment\x00" + secret),
                  chunk(b"zTXt", b"Comment\x00\x00" + z.compress(secret))):
            with open(os.path.join(self.dir, "logo.png"), "wb") as f:
                f.write(b"\x89PNG\r\n\x1a\n" + c + chunk(b"IEND", b""))
            rc, out = self.scan(self.dir)
            self.assertIn("github-token", out)

    def test_file_link_target_is_scanned_not_followed(self):
        harmless = os.path.join(self.dir, "harmless.md")
        with open(harmless, "w") as f:
            f.write("nothing\n")
        os.symlink("/" + "Users/Alice/private.md", os.path.join(self.dir, "alias.md"))
        rc, out = self.scan(self.dir)
        self.assertIn("alias.md:0: home-path", out)

    def test_png_tricks(self):
        import struct
        import zlib as z
        def chunk(kind, body):
            return (struct.pack(">I", len(body)) + kind + body
                    + struct.pack(">I", z.crc32(kind + body)))
        sig = b"\x89PNG\r\n\x1a\n"
        token = "gh" + "p_" + "H" * 36
        cases = {
            "trailing": sig + chunk(b"IEND", b"") + token.encode(),
            "exif-utf16": sig + chunk(b"eXIf", b"MM\x00*" + token.encode("utf-16-be"))
                          + chunk(b"IEND", b""),
            "bomb": sig + chunk(b"zTXt", b"k\x00\x00" + z.compress(b"a" * (3 * 1024 * 1024)))
                    + chunk(b"IEND", b""),
        }
        for name, data in cases.items():
            with open(os.path.join(self.dir, "logo.png"), "wb") as f:
                f.write(data)
            rc, out = self.scan(self.dir)
            self.assertEqual(rc, 1, (name, out))

    def test_unreadable_and_symlinked_directories_are_reported(self):
        locked = os.path.join(self.dir, "locked")
        os.makedirs(locked)
        self.write("locked/k.md", "x\n")
        outside = tempfile.mkdtemp(prefix="corun-outside-")
        os.symlink(outside, os.path.join(self.dir, "linked"))
        os.chmod(locked, 0)
        try:
            rc, out = self.scan(self.dir)
        finally:
            os.chmod(locked, 0o700)
            shutil.rmtree(outside, ignore_errors=True)
        self.assertEqual(rc, 1, out)
        self.assertIn("unreadable directory", out)
        self.assertIn("symlinked directory", out)

    def test_skill_itself_is_clean(self):
        rc, out = self.scan(SKILL)
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
