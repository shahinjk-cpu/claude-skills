---
name: verbatim-prompting
description: >-
  Prompt invariance and verbatim token copying methodology that eliminates semantic drift across multi-step agent generations.
---

# Verbatim Prompting Protocol

Semantic drift occurs when agents rephrase or paraphrase prompt segments across sequential steps. Verbatim prompting locks critical phrases word-for-word.

## Execution Rules
1. **Never Paraphrase Invariant Tokens**: When describing a locked character or design token, copy the exact string from the Asset Passport.
2. **Explicit Bracket Notation**: Enclose invariant sections in verbatim markers:
   `[VERBATIM_ANCHOR: 'matte black cybernetic arm with orange fiber-optic seams']`
3. **Diff Verification**: Before passing prompts to generators, verify that invariant tokens have zero Levenshtein distance against the baseline.
