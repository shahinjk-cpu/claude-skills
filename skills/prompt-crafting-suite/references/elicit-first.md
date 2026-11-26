---
name: elicit-first
description: Structured requirements elicitation and ambiguity resolution before implementation. Use when a user describes a task, feature, or logic to implement before writing any code or solution.
---

# Skill: Structured Requirements Elicitation

**Trigger:** Use this skill when a user describes a task, feature, or logic to implement — before writing any code or solution.

**Language:** Respond in the language of the conversation or as specified by the user. This prompt is in English to save tokens.

---

## RULES (always active)

- ❌ Never write code, SQL, scripts, or implementation until the user says **"приступай к реализации"** / **"start implementation"** / **"proceed"**
- ✅ Always complete all 3 phases before implementation
- ✅ Keep responses tight — no filler, no repetition
- ✅ Format questions as a clean matrix with lettered options (a/b/c)
- ✅ After each phase, wait for user response before continuing

---

## PHASE 1 — Ambiguity Matrix

When the user gives a task:

1. Read silently. Identify all decision points (if/else branches, edge cases, unknowns)
2. Group them into categories (A, B, C, D…) — one category per logical domain
3. Output a formatted matrix:

```
## 📋 Phase 1 — Clarifying Questions

**[Category A: <domain name>]**
A1. <question>?
    (a) <option>
    (b) <option>
    (c) <option>

**[Category B: <domain name>]**
B1. <question>?
    (a) <option>
    (b) <option>

... etc.

> Answer each (e.g. A1→b, B1→a) — I'll build the flowchart after.
```

Keep questions minimal — cover maximum ambiguity with minimum questions. Aim for 4–8 questions total.

---

## PHASE 2 — Correction Round

After the user answers Phase 1:

1. Acknowledge answers briefly (1 line per answer max)
2. Identify any new ambiguities revealed by their answers
3. If none → skip to Phase 3
4. If yes → output only the delta questions:

```
## 🔁 Phase 2 — Follow-up

**[Category X: <new domain revealed>]**
X1. <question>?
    (a) <option>
    (b) <option>

> Answer, then I'll finalize.
```

Never re-ask answered questions. Never exceed 4 follow-up questions.

---

## PHASE 3 — Flowchart + Confirmation

After Phase 2 answers (or if Phase 2 was skipped):

1. Build a structured flowchart in text/ASCII covering all scenarios
2. Summarize key decisions as a compact table
3. End with confirmation gate:

```
## ✅ Phase 3 — Logic Map

[flowchart here]

**Decision summary:**
| Scenario | Action |
|----------|--------|
| ...      | ...    |

---
> Does this match your intent? If yes — say **"proceed"** to start implementation.
> If something's off — tell me what to fix.
```

---

## FLOWCHART FORMAT

Use this ASCII style for logic:

```
START
  └─ Condition?
       ├─ YES → sub-condition?
       │          ├─ YES → Action A
       │          └─ NO  → Action B
       └─ NO  → Action C
```

Keep it readable. One branch per line. No walls of text.

---

## EXAMPLE TRIGGER PHRASES

This skill activates when user says things like:
- "нужно реализовать логику..."
- "implement logic for..."
- "сделай функцию которая..."
- "build a system that..."
- any description of business logic, data processing, or multi-step behavior

---

## TOKEN ECONOMY RULES

- No greetings, no "Great question!", no summaries of what the user just said
- Use symbols (→, ✅, ❌, ├─, └─) instead of words where possible
- Tables > bullet lists > prose (in that order of preference)
- Phase headers are the only bold headers needed

