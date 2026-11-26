# Model refresh

Run when a vendor releases a model that could fill a role, when a partner CLI drops a model, or when `models.json` is more than about two months old.

1. **List candidates.** For each vendor, the current models the CLI offers (`agy models`, `grok models`, the Codex model list) and the newest announced models.
2. **Gather** with the runner, one task per model, in parallel:
   - the vendor's model card or system card: stated uses, strengths with effort level, limitations, effort levels;
   - published benchmarks per task type, one task per type: coding agents, code review (precision and recall), hallucination or factual accuracy, writing quality.
3. **Verify.** Claude opens each primary page that a role decision rests on and marks every figure: confirmed on the primary page, confirmed only on an aggregator, or unverified.
4. **Decide roles** at the effort levels the user is willing to pay for (default `high`). Compare only figures measured at that effort, or say that none exist.
5. **Record.** Replace `reference/evidence.md` with the new dated evidence, with a source URL for every figure. Edit `models.json`: partner models and efforts, role chains, and the `updated` date. If the user keeps an override in `~/.config/corun/models.json`, edit that file instead, since it takes precedence.
6. **Re-check.** Run `corun.py check` and show the user the new declaration together with what changed and why.
