---
name: prompt-context-engineer
description: >-
  Designs, audits, and optimizes system prompts, agent instructions, structured outputs,
  few-shot examples, and context architectures for LLMs (Gemini, Claude, GPT). Use when
  the user wants to write, improve, debug, or evaluate prompts, build AI personas,
  create SKILL.md files, or design agentic tool-calling instructions.
---

# Prompt & Context Engineering Master

Use this skill whenever crafting, refactoring, or debugging prompts, system instructions, agent workflows, or LLM schemas.

## 1. Core Architecture of a Production Prompt

Structure every complex system prompt using clear, unambiguous sections (Markdown headers or XML tags):

```xml
<role>
Define the exact expertise, domain, tone, and operational boundaries of the AI.
</role>

<context>
Provide background knowledge, domain constraints, and environment state.
Keep static content at the top to maximize Prompt Caching hit rates.
</context>

<instructions>
1. Numbered, deterministic step-by-step workflow.
2. Explicit decision trees ("If X, do A; if Y, do B").
3. Tool usage rules (when to call a tool vs. when to answer directly).
</instructions>

<constraints>
- Negative constraints stated positively where possible ("Always validate JSON against X" instead of "Don't output bad JSON").
- Hallucination guardrails ("If the answer is not in the provided context, state explicitly what is missing").
</constraints>

<output_format>
Exact structure, schema, language, and length expectations.
</output_format>
```

## 2. Advanced Techniques

1. **Context Engineering & Prompt Caching**:
   - Place static instructions, schemas, and few-shot examples at the **beginning** of the prompt.
   - Place dynamic user input, retrieved RAG chunks, and current session state at the **end**.
2. **Structured Outputs (Schema-First)**:
   - When an application consumes LLM output programmatically, enforce native `response_schema` / JSON Schema with strict types, enums, and descriptions on every field instead of relying on prose instructions alone.
3. **Few-Shot Calibration**:
   - Include 2–3 diverse, high-signal `<example>` pairs covering edge cases (e.g., ambiguous input, missing data, complex formatting) rather than 10 repetitive basic examples.
4. **Reasoning & Verification (Chain-of-Thought / Self-Critique)**:
   - For non-trivial logic, instruct the model to verify constraints before producing the final output (or leverage native thinking budgets paired with a concise verification checklist).
5. **Tool-Calling Precision**:
   - Write tool descriptions that specify **what** the tool does, **when** to call it, and **when NOT** to call it.

## 3. Prompt Debugging & Evaluation Checklist

When a prompt fails or behaves inconsistently, diagnose using this sequence:
- **Ambiguity Check**: Are two rules contradicting each other?
- **Lost-in-the-Middle**: Is a critical instruction buried in the middle of a 10,000-token block? Move it to the very top or very bottom.
- **Format Drift**: Add 1 concrete input->output example demonstrating the exact target format.
- **Over-Triggering / Under-Triggering**: Tighten the trigger condition with explicit positive and negative examples.
