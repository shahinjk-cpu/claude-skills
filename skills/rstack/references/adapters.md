# Launching builders and reviewers on different models

Check each CLI's `--help` for the flags your installation supports.

## Claude subagents (inside a Claude Code session)

Use the Agent tool with a `model` (for example `opus` for hard work, `sonnet` for reviews or cause reads when cost matters, `haiku` for trivial lookups) and `run_in_background: true` for anything long. `isolation: "worktree"` gives the agent its own git worktree. The brief is everything it knows.

- Launch independent agents in one turn so they run in parallel.
- Never predict a background agent's result; wait for its notification.
- Re-address a finished agent with SendMessage to continue it with its context.

## OpenAI Codex CLI

Good as an independent reviewer of Claude-built work, and as a builder for well-specified parts.

```
codex exec -m <model> -C <worktree> --sandbox workspace-write "$(cat brief.md)"
```

- `--sandbox workspace-write` lets it edit only inside the worktree; use `read-only` for reviews.
- A builder that must also write a verdict or report outside the worktree needs that path made writable or its text returned instead.
- Have it return text. For builds, the launching window reads the diff, tests it, commits and opens a draft PR.

## opencode (any of its models: DeepSeek, Kimi, Muse, Qwen, GLM and more)

`opencode models` lists what this machine can use: opencode's own hosted models (some free, for example `opencode/deepseek-v4.1-flash-free`), and any provider you sign in to (`opencode auth login`): DeepSeek, Moonshot (Kimi), OpenRouter, and others. Pick by the task's difficulty grade; the guard is the same for all of them. Use the wrapper for non-interactive runs:

```sh
scripts/oc-build.sh <worktree> <brief-file> <log-file> <provider/model>
```

The wrapper refuses the shared root checkout. It clears named credential variables and applies the command and path deny list in `scripts/opencode-guard.json`. Test it with a dummy credential file and a cloud CLI command. Both should be refused. A plain worktree edit should pass. Use an outer sandbox with no credentials or network for untrusted code. See [trust and access](trust.md).

## OpenRouter models

Three ways, by what the job needs:
- **Builder with tools**: opencode with the OpenRouter provider (`opencode auth login`, then `-m openrouter/<vendor>/<model>`), through the same guarded wrapper as any opencode model.
- **Read-only job over the API** (a review, a plan-panel seat, a cause read over logs, a summary): `scripts/openrouter-ask.py --model <vendor/model> --brief brief.md --file a.py --file b.py --out answer.md`, or the `openrouter` subagent, which runs it. The model sees only the brief and the files you name, and cannot run anything. The script checks attachment path names and caps total text size. Check the brief and attachments for sensitive content before sending.
- **Reviewer through Codex CLI**: point Codex at OpenRouter through its provider config, for review jobs.

Keep the key in the OS keychain (the script reads `OPENROUTER_API_KEY` or a keychain item, default `openrouter-api`); never in a file, a log or a brief. Set a spend limit on the OpenRouter key itself.

### OpenRouter for API tasks

OpenRouter is also the easiest way to give a pipeline or a one-off job programmatic access to hundreds of models through one key and one API. Use it for work that is too many or too repetitive for an agent:
- classifying or labelling records, extracting fields into JSON, normalising messy text;
- summarising or translating many documents or strings;
- generating test fixtures, edge-case inputs or copy variants;
- grading outputs against a rubric (model-as-judge) and comparing several models on the same inputs before choosing one for a product feature.

`scripts/openrouter-batch.py` runs one prompt template over a JSONL file of items: bounded concurrency, retries with backoff on rate limits, optional JSON-only output that is checked to parse, a spend threshold (`--max-cost-usd`, from the cost OpenRouter reports), and resume (completed items are skipped). The threshold stops new requests once reported spend reaches it. Requests already in flight can exceed it. Start with `--max-items 20` on a cheap model and have an agent check a sample before running the rest.

When the task is part of the product (the app itself calls a model), the same key pattern applies in the service: the key in the secret store, a spend limit on the key, a per-request timeout and retry budget, and the model id in configuration so it can be switched without a deploy.

## The shared test-slot lock

Many agents on one laptop will run test suites at the same time and exhaust memory. Put every heavy local run behind one lock with a few slots:

```
scripts/run-slot.sh pytest -q -n 2 tests/test_my_part.py
```

`scripts/run-slot.sh` keeps a first-come queue of tickets, archives each ticket when its run exits, and scans the queue without forking a process per ticket. Set `RUN_SLOTS` from `caps.local_heavy_run_slots` and adjust it for the machine. Watch memory across worktrees and stop idle runs you own first.

If a resource is shared by a whole step (one local database, one port), take the slot lock FIRST and the resource lock INSIDE it, so a waiter never holds the scarce resource while queuing for a slot.
