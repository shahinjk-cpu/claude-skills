# Universal Skill Router & Auto-Activation Rules

The workstation hosts a curated suite of **5,101 expert skills**.

## 🛡️ Core 22 Mandatory Always-Active Skills (Enforced on Every Operation)

Regardless of the user prompt or domain, the following 22 foundational skills are **PERMANENTLY ACTIVE**:
1. `token-budget-advisor`: Real-time context budget calculation & prompt condensation.
2. `compact-conversation`: Intelligent compression of conversation history without losing critical decisions.
3. `ai-session-optimizer`: Minimizes turn roundtrips and optimizes latency.
4. `prompt-caching-strategy`: Exploits prompt prefix caching for dramatic token reduction.
5. `clean-code`: Direct, pragmatic implementation without over-engineering or AI comments.
6. `anti-slop-ui`: Enforces high-craft aesthetic standards and blocks generic AI styles.
7. `memory-safety-patterns`: Stack vs heap discipline, memory leak avoidance, safe resource release.
8. `file-system-memory`: Long-term state and memory persistence using local files rather than chat history.
9. `error-handling-patterns`: Resilient exception handling and graceful recovery protocols.
10. `verification-loop`: Mandatory compile/run/test validation before completing tasks.
11. `gateguard`: Fact-forcing gate requiring proof of interfaces before modification.
12. `zero-hallucination-coder`: Strict rule against guessing commands, imports, or file locations.
13. `code-simplification`: Complexity reduction and entropy minimization.
14. `security-best-practices`: Secret protection, credential isolation, and secure shell escaping.
15. `universal-skill-router`: Dynamic automatic dispatch to relevant domain expert skills.
16. `session-guard`: State consistency across interruptions, reboots, and agent handoffs.
17. `work_efficiently`: Parallel execution of independent tool calls in a single turn.
18. `git-safety-net`: Atomic, cleanly structured commits for easy rollback.
19. `locked-references`: Protection of user requirements, constants, and business constraints.
20. `written-gates-generation`: Clear milestones and measurable acceptance criteria.
21. `inferssd`: Memory-mapped offloading for heavy local AI and data tasks.
22. `typegpu`: Type-safe hardware execution standards.

## Mandatory Dynamic Routing Protocol

1. **Auto-Route Matching Skills**:
   For any task involving web design, mobile development, backend APIs, databases, game dev, AI agents, automation, security audits, or testing, the agent MUST automatically identify and load the relevant specialized skill(s).

2. **Skill Discovery via Router**:
   - Check the Master Catalog: `skills_manifest.json` (or `skills_index.md`).
   - Or execute: `python skill_router.py "<keywords>"`.

3. **Mandatory Progressive Reading**:
   - Before taking action or writing code, read the chosen skill's `SKILL.md` using `read_file`.
   - Apply the architectural standards, code quality checks, and workflows defined in the skill.
