---
name: token-quota-optimizer
description: >-
  Optimizes token usage, context window efficiency, and tool call quota using YAGNI
  (You Aren't Gonna Need It) and lean-context principles. Use when writing code,
  exploring large codebases, refactoring, or when the user asks for quota-efficient,
  minimal, fast, and concise execution.
---

# Token & Quota Optimizer (YAGNI + Lean Context)

Inspired by `DietrichGebert/ponytail` (YAGNI) and `yvgude/lean-ctx`, this skill enforces strict context-window hygiene, minimal code generation, and tool-call batching to save up to 50% of token and request quota.

## 1. Context Hygiene & File Reading Rules

1. **Never Read Whole Large Files Blindly**:
   - Before reading a file >200 lines, search for symbols or keywords first (`grep_search` or `find_by_name`).
   - Use `StartLine` and `EndLine` in `view_file` to inspect only the relevant slice (±40 lines around the match).
2. **Batch Parallel Tool Calls**:
   - Whenever multiple independent files, searches, or URLs need to be inspected, invoke all read/search tools in a **single turn** in parallel rather than sequential turns.
   - Each extra turn re-sends the entire conversation history; fewer turns = massive quota savings.
3. **Avoid Redundant Re-Reads**:
   - Trust the file contents already in your recent context unless an external command modified the file.
4. **Filter Command Outputs**:
   - When running shell commands that can produce huge logs (`git log`, `npm list`, directory listings, JSON dumps), always limit output (`-n 20`, `--depth=1`, `Select-Object -First 30`, or `jq` filters).

## 2. YAGNI Coding Principles ("The Best Code is the Code You Never Wrote")

1. **Solve Only What Was Asked**:
   - Do not build speculative abstractions, generic factories, or unrequested configuration layers for a single use case.
   - Three similar lines of clear code are better than a premature helper class.
2. **Surgical Edits Over Full Rewrites**:
   - Always prefer `replace_file_content` on specific line ranges rather than rewriting entire files.
   - Touch only the lines necessary to achieve the goal; preserve surrounding formatting and comments.
3. **Zero Boilerplate Bloat**:
   - Do not add verbose comments that merely restate what the code does (e.g., `// increment i`). Comment only non-obvious *why* decisions or invariants.
   - Avoid adding unnecessary dependencies if the standard library or already-installed packages solve the problem.

## 3. Concise Communication

1. **No Code Echoing**:
   - After editing a file with a tool, do **not** paste the entire file or large code block again in the chat response. Summarize the change in 2–4 bullet points with clickable file/symbol links.
2. **Direct Answers First**:
   - Start responses with the direct solution or action taken. Skip filler introductions and repetitive summaries.
