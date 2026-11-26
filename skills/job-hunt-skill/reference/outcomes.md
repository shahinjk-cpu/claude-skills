# Outcome log

Every change to `applications.md` also gets an event in `outcomes/outcomes.jsonl` (schema: the workspace's `outcomes/README.md`). `filter.py` logs scan decisions automatically.
```bash
python3 SKILL_DIR/scripts/outcomes.py --workspace <ws> event --company C --title T --event decision --value applied --data '{"channel": "greenhouse"}'
python3 SKILL_DIR/scripts/outcomes.py --workspace <ws> event --company C --title T --event stage --value interview --data '{"format": "video-call", "round": 1, "scheduled": "YYYY-MM-DD"}'
python3 SKILL_DIR/scripts/outcomes.py --workspace <ws> stats       # funnel
python3 SKILL_DIR/scripts/outcomes.py --workspace <ws> calibrate   # does the fit score predict interviews? (advisory)
```
- **Skips are the most useful labels.** When the user passes on a kept job, log `decision skipped` with a reason code; ask why if it isn't clear.
- **One case stays one case.** If a correction sounds general, ask: "Should this apply to all X, or only this job?" Log `rule proposed`. Only after the user confirms it and it's in `filters.md`/`memory.md`, log `rule approved` with `--reply` holding their words verbatim. To drop one role but keep the company, use `excludedRoles`.
- **Calibration is advisory.** Relay `calibrate` as printed; with few outcomes it shows counts or "insufficient". Fit weights change only when the user decides.
- **Interviews:** put `data.scheduled` on stage events so `insights.py due` can remind the user.
- **Follow-ups:** when the user nudges a company, log `stage followed_up`; `due` then stays quiet about it for 7 days.
- **Retention:** after a hire, `insights.py due` lists check-ins at 30, 90, 180 and 365 days. Ask briefly (satisfaction 1–5, did the job match the posting 1–5, would stay) and log `checkin`. The posting saved at apply time (`outcomes/postings/`) is the reference.
- **Privacy:** roles ("recruiter"), not names, in notes and data. To erase someone: `outcomes.py redact "Name" "email"`. To share (opt-in only): `outcomes.py export`, which keeps codes and coarse features only; show the user the file first.
